import os
import copy
import time
import random
import numpy as np

class Game:

    LAYOUT = "0-2-o,5-5-x,7-3-x,11-5-o,12-5-x,16-3-o,18-5-o,23-2-x"
    NUMCOLS = 24
    QUAD = 6
    OFF = 'off'
    ON = 'on'

    TOKENS = ['o', 'x']

    def __init__(self, layout=LAYOUT, grid=None, off_pieces=None,
                 bar_pieces=None, num_pieces=None, players=None):
        """
        Define a new game object
        """
        self.die = Game.QUAD
        self.layout = layout
        if grid:
            self.grid = copy.deepcopy(grid)
            self.off_pieces = copy.deepcopy(off_pieces)
            self.bar_pieces = copy.deepcopy(bar_pieces)
            self.num_pieces = copy.deepcopy(num_pieces)
            self.players = players
            return
        self.players = Game.TOKENS
        self.grid = [[] for _ in range(Game.NUMCOLS)]
        self.off_pieces = {}
        self.bar_pieces = {}
        self.num_pieces = {}
        for t in self.players:
            self.bar_pieces[t] = []
            self.off_pieces[t] = []
            self.num_pieces[t] = 0

    @staticmethod
    def new():
        game = Game()
        game.reset()
        return game

    # def extract_features(self, player):
    #     features = []
    #     for p in self.players:
    #         for col in self.grid:
    #             feats = [0.] * 6
    #             if len(col) > 0 and col[0] == p:
    #                 for i in range(len(col)):
    #                     feats[min(i, 5)] += 1
    #             features += feats
    #         features.append(float(len(self.bar_pieces[p])) / 2.)
    #         features.append(float(len(self.off_pieces[p])) / self.num_pieces[p])
    #     if player == self.players[0]:
    #         features += [1., 0.]
    #     else:
    #         features += [0., 1.]
    #     return np.array(features).reshape(1, -1)

    def extract_features(self, player):
        """
        custom feature extraction of
        https://github.com/TobiasVogt/TD-Gammon/blob/master/TD-Gammon.ipynb

        Parameters
        ----------
        player : TYPE
            DESCRIPTION.

        Returns
        -------
        TYPE
            DESCRIPTION.

        """
        features = []
        # 196 Features kodieren den Zustand der Spielfelder, 98 für jeden Spieler
        for p in self.players:
            # 24 mögliche Brettpositionen
            for col in self.grid:
                # 4 Features kodieren eine Stelle auf dem Spielbrett
                feats = [0.] * 4
                if len(col) > 0 and col[0] == p:
                    # 0,1,2,3,4,5 Steine werden kodiert als
                    # 0000, 1000, 1100, 1110, 1110.5, 1111
                    # (4. Bit = (n-3)/2)
                    for i in range(len(col)):
                        if i < 3:
                            feats[i] += 1
                        else:
                            feats[3] = (len(col)-3)/2.0
                            break
                features += feats
            # Anzahl der Steine auf der "Bar", n/2
            features.append(float(len(self.bar_pieces[p])) / 2.)
            # Anzahl der Steine die bereits aus dem Spiel sind, n/15
            features.append(float(len(self.off_pieces[p])) / 15.)
        # Zwei Features für den derzeitigen Spieler
        if player == self.players[0]:
            features += [1., 0.]
        else:
            features += [0., 1.]
        return np.array(features).reshape(1, -1)

    def roll_dice(self):
        return (random.randint(1, self.die), random.randint(1, self.die))

    def play(self, players, draw=False):
        player_num = random.randint(0, 1)
        while not self.is_over():
            self.next_step(players[player_num], player_num, draw=draw)
            player_num = (player_num + 1) % 2
        return self.winner()

    def next_step(self, player, player_num, draw=False):
        roll = self.roll_dice()

        if draw:
            self.draw()

        self.take_turn(player, roll, draw=draw)

    def take_turn(self, player, roll, draw=False):
        if draw:
            print("Player %s rolled <%d, %d>." % (player.player, roll[0], roll[1]))
            time.sleep(1)

        # moves = self.get_actions(roll, player.player, nodups=True)
        moves = self.get_actions_doubles(roll, player.player, nodups=True)
        # original
        # print(moves)
        # moves = self.getActions(roll, player.player)
        move = player.get_action(moves, self) if moves else None
        # print("Player %s rolled <%d, %d>." % (player.player, roll[0], roll[1]))
        # print("--- end ---")
        if move:
            self.take_action(move, player.player)

    def clone(self):
        """
        Return an exact copy of the game. Changes can be made
        to the cloned version without affecting the original.
        """
        return Game(None, self.grid, self.off_pieces,
                    self.bar_pieces, self.num_pieces, self.players)

    def take_action(self, action, token):
        """
        Makes given move for player, assumes move is valid,
        will remove pieces from play
        """
        # print(action)
        # print(self.bar_pieces)
        # print(" -- ")
        ateList = [0] * 4
        for i, (s, e) in enumerate(action):
            if s == Game.ON:
                piece = self.bar_pieces[token].pop()
            else:
                piece = self.grid[s].pop()
            if e == Game.OFF:
                self.off_pieces[token].append(piece)
                continue
            if len(self.grid[e]) > 0 and self.grid[e][0] != token:
                bar_piece = self.grid[e].pop()
                self.bar_pieces[bar_piece].append(bar_piece)
                ateList[i] = 1
            self.grid[e].append(piece)
        return ateList

    def undo_action(self, action, player, ateList):
        """
        Reverses given move for player, assumes move is valid,
        will remove pieces from play
        """
        for i, (s, e) in enumerate(reversed(action)):
            if e == Game.OFF:
                piece = self.off_pieces[player].pop()
            else:
                piece = self.grid[e].pop()
                if ateList[len(action) - 1 - i]:
                    bar_piece = self.bar_pieces[self.opponent(player)].pop()
                    self.grid[e].append(bar_piece)
            if s == Game.ON:
                self.bar_pieces[player].append(piece)
            else:
                self.grid[s].append(piece)

    # def getActions(self, roll, token):
    #     """
    #     Get set of all possible move tuples
    #     """
    #     moves = set()

    #     r1,r2 = roll
    #     if token == self.players[1]:
    #         r1,r2 = -r1,-r2

    #     rolls = [(r1,r2),(r2,r1)]
    #     # print("player {} rolled {}".format(token, rolls))

    #     offboarding = self.can_offboard(token)
    #     for r1,r2 in rolls:
    #         for i in range(len(self.grid)):
    #             if self.is_valid_move(i, i+r1 , token):
    #                 move1 = (i,i+r1)
    #                 piece = self.grid[i].pop()

    #                 bar_piece = None
    #                 if len(self.grid[i+r1])==1 and self.grid[i+r1][-1] != token:
    #                     bar_piece = self.grid[i+r1].pop()

    #                 self.grid[i+r1].append(piece)
    #                 self.get_second_move(token, r2, moves, move1)
    #                 self.grid[i+r1].pop()
    #                 self.grid[i].append(piece)
    #                 if bar_piece:
    #                     self.grid[i+r1].append(bar_piece)
    #             # print("player {} - offboarding : {} - remove piece {} ".format(token, offboarding, self.remove_piece(token,i,r1)))
    #             if offboarding and self.remove_piece(token,i,r1):
    #                 move1 = (i, self.OFF)
    #                 piece = self.grid[i].pop()

    #                 self.off_pieces[token].append(piece)
    #                 self.get_second_move(token,r2,moves,move1,offboarding)
    #                 if len(self.off_pieces[token])+len(self.bar_pieces[token])==self.num_pieces[token]:
    #                     moves.add((move1,))
    #                 self.off_pieces[token].pop()
    #                 self.grid[i].append(piece)

    #     # has no moves, try moving only one piece
    #     if not moves:
    #         for i in range(len(self.grid)):
    #             for r in rolls[0]:
    #                 if self.is_valid_move(i,i+r,token):
    #                     move1 = (i,i+r)
    #                     moves.add((move1,))

    #     # print("player {} moves {}".format(token, moves))
    #     return moves

    def get_actions_doubles(self, roll, player, nodups=False):
        """
        Get set of all possible move tuples with doubles, custom added
        """
        moves = set()
        if nodups:
            start = 0
        else:
            start = None

        r1, r2 = roll

        if player == self.players[1]:
            r1,r2 = -r1,-r2
        rolls = []
        rolls.append(r1)
        rolls.append(r2)
        # print(rolls)
        # print("player {} rolled {} - {}".format(player, r1,r2))
        if r1 == r2: # doubles
            i = 4
            # keep trying until we find some moves
            while not moves and i > 0:
                self.find_moves(tuple([r1]*i), player, (), moves, start)
                i -= 1
        else:
            self.find_moves((r1, r2), player, (), moves, start)
            self.find_moves((r2, r1), player, (), moves, start)
            # has no moves, try moving only one piece
            if not moves:
                for r in rolls:
                    self.find_moves((r, ), player, (), moves, start)
        # print("player {} - mooves ========== ".format(player))
        # for m in moves:
        #     print(m)

        return moves

    def get_actions(self, roll, player, nodups=False):
        """
        Get set of all possible move tuples original with anti clockwise
        """
        moves = set()
        if nodups:
            start = 0
        else:
            start = None

        r1, r2 = roll

        if player == self.players[1]:
            r1, r2 = -r1, -r2

        # print("player {} rolled {} - {}".format(player, r1,r2))
        if r1 == r2: # doubles
            i = 4
            # keep trying until we find some moves
            while not moves and i > 0:
                self.find_moves(tuple([r1]*i), player, (), moves, start)
                i -= 1
        else:
            self.find_moves(roll, player, (), moves, start)
            self.find_moves((r2, r1), player, (), moves, start)
            # has no moves, try moving only one piece
            if not moves:
                for r in roll:
                    self.find_moves((r, ), player, (), moves, start)
        # print("player {} - mooves ========== ".format(player))
        # for m in moves:
        #     print(m)

        return moves

    # def find_moves_original(self, rs, player, move, moves, start=None):
    #     if len(rs) == 0:
    #         moves.add(move)
    #         return
    #     r, rs = rs[0], rs[1:]

    #     # see if we can remove a piece from the bar
    #     if self.bar_pieces[player]:
    #         if self.can_onboard(player, r):
    #             piece = self.bar_pieces[player].pop()
    #             bar_piece = None
    #             if len(self.grid[r - 1]) == 1 and self.grid[r - 1][-1] != player:
    #                 bar_piece = self.grid[r - 1].pop()

    #             self.grid[r - 1].append(piece)

    #             self.find_moves(rs, player, move+((Game.ON, r - 1), ), moves, start)
    #             self.grid[r - 1].pop()
    #             self.bar_pieces[player].append(piece)
    #             if bar_piece:
    #                 self.grid[r - 1].append(bar_piece)
    #         return

    #     # otherwise check each grid location for valid move using r
    #     offboarding = self.can_offboard(player)

    #     for i in range(len(self.grid)):
    #         if start is not None:
    #             start = i
    #         if self.is_valid_move(i, i + r, player):

    #             piece = self.grid[i].pop()
    #             bar_piece = None
    #             if len(self.grid[i+r]) == 1 and self.grid[i+r][-1] != player:
    #                 bar_piece = self.grid[i + r].pop()
    #             self.grid[i + r].append(piece)
    #             self.find_moves(rs, player, move + ((i, i + r), ), moves, start)
    #             self.grid[i + r].pop()
    #             self.grid[i].append(piece)
    #             if bar_piece:
    #                 self.grid[i + r].append(bar_piece)

    #         # If we can't move on the board can we take the piece off?
    #         # if(player == self.players[1]):
    #         #     print("offboarding : {} - offboarding {} ".format(offboarding, self.remove_piece(player, i, r)))

    #         if offboarding and self.remove_piece(player, i, r):
    #             piece = self.grid[i].pop()
    #             self.off_pieces[player].append(piece)
    #             self.find_moves(rs, player, move + ((i, Game.OFF), ), moves, start)
    #             self.off_pieces[player].pop()
    #             self.grid[i].append(piece)

    def find_moves(self, rs, player, move, moves, start=None):
        """
        custom function to find mooves
        problems -> can create some moove like : ('on', -4), (7, 3)

        Parameters
        ----------
        rs : TYPE
            DESCRIPTION.
        player : TYPE
            DESCRIPTION.
        move : TYPE
            DESCRIPTION.
        moves : TYPE
            DESCRIPTION.
        start : TYPE, optional
            DESCRIPTION. The default is None.

        Returns
        -------
        None.

        """
        if len(rs) == 0:
            moves.add(move)
            return
        r, rs = rs[0], rs[1:]

        # see if we can remove a piece from the bar
        if self.bar_pieces[player]:
            if self.can_onboard(player, r):

                # print("moove on for player {}".format(player))
                # print(self.bar_pieces[player])
                piece = self.bar_pieces[player].pop()
                bar_piece = None
                if(player == self.players[0]):
                    start_onboard = 0
                    # print("ON to {}".format(start_onboard + r - 1))
                    # print("piece bar {}".format(piece))

                    if len(self.grid[start_onboard + (r - 1)]) == 1 and self.grid[start_onboard + (r - 1)][-1] != player:
                        bar_piece = self.grid[start_onboard + (r - 1)].pop()

                        self.bar_pieces[Game.TOKENS[1]].append(bar_piece)

                    self.grid[start_onboard + (r - 1)].append(piece)

                    # add the moove ON (the bar) to dice value to the list of moves and kick the dice value
                    self.find_moves(rs, player, move+((Game.ON, start_onboard + r - 1), ), moves, start)

                    self.grid[start_onboard + (r - 1)].pop()
                    self.bar_pieces[player].append(piece)

                    # if we kicked piece of other player TODO -> check if we put this before the recursive call
                    if bar_piece:
                        self.grid[start_onboard + (r - 1)].append(bar_piece)
                        self.bar_pieces[Game.TOKENS[1]].pop()

                else:
                    start_onboard = 23

                    if len(self.grid[start_onboard + (r + 1)]) == 1 and self.grid[start_onboard + (r + 1)][-1] != player:
                        bar_piece = self.grid[start_onboard + (r + 1)].pop()

                        self.bar_pieces[Game.TOKENS[0]].append(bar_piece)

                    self.grid[start_onboard + (r + 1)].append(piece)
                    # print("moove on for player x")
                    # add the moove ON (the bar) to dice value to the list of moves and kick the dice value
                    self.find_moves(rs, player, move+((Game.ON, start_onboard + r + 1), ), moves, start)

                    self.grid[start_onboard + (r + 1)].pop()
                    self.bar_pieces[player].append(piece)

                    # if we kicked piece of other player
                    if bar_piece:
                        self.grid[start_onboard + (r + 1)].append(bar_piece)
                        self.bar_pieces[Game.TOKENS[0]].pop()

                return

        # otherwise check each grid location for valid move using r
        offboarding = self.can_offboard(player)

        for i in range(len(self.grid)):
            if start is not None:
                start = i

            # if the moove from i to i+ roll is valid for the player
            if self.is_valid_move(i, i + r, player):
                # remove the piece at position i
                piece = self.grid[i].pop()
                bar_piece = None

                 #if we can kick the other player token
                if len(self.grid[i+r]) == 1 and self.grid[i+r][-1] != player:
                    bar_piece = self.grid[i + r].pop()

                    self.bar_pieces[Game.TOKENS[1 - Game.TOKENS.index(player)]].append(bar_piece)

                # add our piece
                self.grid[i + r].append(piece)

                # find other mooves with the rest of the dices
                self.find_moves(rs, player, move + ((i, i + r), ), moves, start)

                # re set the token to the original position
                self.grid[i + r].pop()
                self.grid[i].append(piece)

                # add the other token that we put on the bar to the grid
                if bar_piece:
                    self.grid[i + r].append(bar_piece)

                    self.bar_pieces[Game.TOKENS[1 - Game.TOKENS.index(player)]].pop()

            # If we can't move on the board can we take the piece off?
            # if(player == self.players[1]):
            #     print("offboarding : {} - offboarding {} ".format(offboarding, self.remove_piece(player, i, r)))

            if offboarding and self.remove_piece(player, i, r): # TODO double check remove piece

                piece = self.grid[i].pop()
                self.off_pieces[player].append(piece)

                self.find_moves(rs, player, move + ((i, Game.OFF), ), moves, start)
                self.off_pieces[player].pop()

                self.grid[i].append(piece)

    def opponent(self, token):
        """
        Retrieve opponent players token for a given players token.
        """
        for t in self.players:
            if t != token:
                return t

    def is_won(self, player):
        """
        If game is over and player won, return True, else return False
        """
        return self.is_over() and player == self.players[self.winner()]

    def is_lost(self, player):
        """
        If game is over and player lost, return True, else return False
        """
        return self.is_over() and player != self.players[self.winner()]

    def reverse(self):
        """
        Reverses a game allowing it to be seen by the opponent
        from the same perspective
        """
        self.grid.reverse()
        self.players.reverse()

    def reset(self):
        """
        Resets game to original layout.
        """
        for col in self.layout.split(','):
            loc, num, token = col.split('-')
            self.grid[int(loc)] = [token for _ in range(int(num))]
        for col in self.grid:
            for piece in col:
                self.num_pieces[piece] += 1

    def winner(self):
        """
        Get winner.
        """
        if len(self.off_pieces[self.players[0]]) > len(self.off_pieces[self.players[1]]):
            return 0
        elif len(self.off_pieces[self.players[0]]) < len(self.off_pieces[self.players[1]]):
            return 1
        else:
            if len(self.bar_pieces[self.players[1]]) <= len(self.bar_pieces[self.players[0]]):
                return 1
            else:
                return 0

        # if (len(self.off_pieces[self.players[0]]) == self.num_pieces[self.players[0]]):
        #     return 0
        # else :
        #     return 1

    def is_over(self):
        """
        Checks if the game is over.
        """
        for t in self.players:
            if len(self.off_pieces[t]) == self.num_pieces[t]:
                return True
        return False

    def can_offboard(self, player):

        # if player is o
        if player == self.players[0]:
            start = Game.NUMCOLS - self.die # 18
            end = Game.NUMCOLS # 24
        # if player 2
        else:
            start = 0 # 0
            end = self.die # 6

        count = 0
        # count if all the players pieces are in the last quarter
        for i in range(start, end):
            if len(self.grid[i]) > 0 and self.grid[i][0] == player:
                count += len(self.grid[i])

        # if(player == self.players[0]):
        #     print("o - count {} ".format(count))
        # else:
        #     print("x - count {} ".format(count))

        # if count + len(self.off_pieces[player]) == self.num_pieces[player]:
        #     return True
        if count + len(self.off_pieces[player]) == self.num_pieces[player]:
            return True

        return False

    def can_onboard(self, player, r):
        """
        Can we take a players piece that is on the bar to a position
        on the grid given by roll-1?
        """
        # set the location of onboarding depending on player
        # if player is o
        if player == self.players[0]:
            start = 0
            # check if the grid position is near empty (1 or 0) or if it's ours
            if len(self.grid[start + (r - 1)]) <= 1 or self.grid[start + (r - 1)][0] == player:
                # print("{} can onboard on {} dice value {}".format(player, start + (r - 1), r))
                return True
            else:
                return False
        # if player 2
        else:
            start = 23
            # print("---")
            # print(start + (r + 1))
            # print("r {}".format(r))

            # dice is negatif so we can keep + but we need to change to +1
            if len(self.grid[start + (r + 1)]) <= 1 or self.grid[start + (r + 1)][0] == player:
                # print("{} can onboard on {} dice value {}".format(player, start + (r + 1), r))
                return True
            else:
                return False

    def remove_piece(self, player, start, r):
        """
        Can we remove a piece from location start with roll r ?
        In this function we assume we are cool to offboard,
        i.e. no pieces on the bar and all are in the home quadrant.
        """
        if player==self.players[0] and start < len(self.grid)-self.die:
            return False
        if player==self.players[1] and start >= self.die:
            return False
        if len(self.grid[start]) == 0 or self.grid[start][0] != player:
            return False



        # player 0 -> remove piece when dice is < O
        if player == self.players[0]:
            if start + r == len(self.grid):
                return True
            if start + r > len(self.grid):
                for i in range(start - 1, len(self.grid) - self.die -1 ,-1):
                    if len(self.grid[i]) != 0 and self.grid[i][0] == self.players[0]:
                        return False
                return True

        # player 1 -> remove piece when dice is < O
        if player == self.players[1]:
            if start+r == -1:
                return True
            if start+r <- 1:
                for i in range(start+1, self.die):
                    if len(self.grid[i]) != 0 and self.grid[i][0]==self.players[1]:
                        return False
                return True

        return False

    def is_valid_move(self, start, end, token):
        # if the grid is not empty and the toke is player
        if len(self.grid[start]) > 0 and self.grid[start][0] == token:
            if end < 0 or end >= len(self.grid):
                return False

            # if there is only one token
            # we can kick the token of someone or it's ours
            if len(self.grid[end]) <= 1:
                return True

            # if there is tokens on the grid and it's players one
            if len(self.grid[end]) > 1 and self.grid[end][-1] == token:
                return True

        return False

    def get_second_move(self,token,r2,moves,move1,offboarding=None):
        if not offboarding:
            offboarding = self.can_offboard(token)
        for j in range(len(self.grid)):
            if offboarding and self.remove_piece(token,j,r2):
                move2 = (j,self.OFF)
                moves.add((move1,move2))

            if self.is_valid_move(j,j+r2,token):
                move2 = (j,j+r2)
                moves.add((move1,move2))

    def draw_col(self,i,col):
        print ("|", end = "")
        if i==-2:
            if col<10:
                print (" ", end = "")
            print (str(col), end = "")
        elif i==-1:
            print ("--", end = "")
        elif len(self.grid[col])>i:
            print (" "+self.grid[col][i], end = "")
        else:
            print ("  ", end = "")

    def draw(self):
        # os.system('clear')
        largest = max([len(self.grid[i]) for i in range(int(len(self.grid)/2),int(len(self.grid)))])
        for i in range(-2,largest):
            for col in range(int(len(self.grid)/2),int(len(self.grid))):
                self.draw_col(i,col)
            print ("|")
        print
        print
        largest = max([len(self.grid[i]) for i in range(int(len(self.grid)/2))])
        for i in range(largest-1,-3,-1):
            for col in range(int(len(self.grid)/2-1),-1,-1):
                self.draw_col(i,col)
            print ("|")
        for t in self.players:
            print ("<Player %s>  Off Board : "%(t), end = "")
            for piece in self.off_pieces[t]:
                print (t+'', end = "")
            print ("   Bar : ", end = "")
            for piece in self.bar_pieces[t]:
                print (t+'', end = "")
            print
