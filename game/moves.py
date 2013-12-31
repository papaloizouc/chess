from itertools import product, chain
from functools import wraps
from math import fabs
from abc import ABCMeta, abstractmethod
import game
from collections import OrderedDict


def _check_range(move: tuple, min_=0, max_=8) -> bool:
    """
        Check if a point is within a range. The default range is 0,8.
    @param move: The move to check
    @param min_: Minimum allowed value of the point (included)
    @param max_: Maximum allowed value of the point (excluded)
    @return: True if in range else False
    """
    return min_ <= move[0] < max_ and min_ <= move[1] < max_


def _slope(start: tuple, end: tuple) -> int:
    """
        For the math formula of the line.
    @return: slope int
    """
    return _safe_divide(start[1] - end[1], start[0] - end[0], default="vertical")


def _line(end: tuple, slope: int=None, start: tuple=None) -> callable:
    """
        Line math formula
    @param slope: Slope for line as generated by _slope
    @return: lambda expression representing the line
    """

    if (slope, start) == ("vertical", None):
        raise TypeError("_line takes either a slope(int) or a start(tuple)")
    if start:
        slope = _slope(start, end)
    if slope is "vertical":  # vertical line
        return lambda x, y: x == end[0]
    return lambda x, y: y - end[1] == slope * (x - end[0])


def _safe_divide(a: int, b: int, default=0) -> int:
    """
        Return 0 if dividing by 0
    """
    if b == 0:
        return default
    return a / b


def _diff_points(start: tuple, end: tuple) -> tuple:
    """
        Calculate a tuple to identify how we move.
        For (3,3),(5,5) will return (-1,-1) identifying that both x and y increase
        (3, 3) (0, 0) will return  (1, 1) identifying that both x and y decrease
    """
    x = start[0] - end[0]
    y = start[1] - end[1]
    return _safe_divide(x, fabs(x)), _safe_divide(y, fabs(y))


def _end_point_check(diff: tuple) -> callable:
    """
        Return lambda to check the endpoint. If moving down the move must be >= than end point else <= than endpoint
    @param diff: Difference of points as produced by _diff_points
    @return: lambda to check if endpoint is in range
    """
    if -1 in (diff[0], diff[1]):
        return lambda move, end: move <= end
    else:
        return lambda move, end: move >= end


def _clean_moves(f):
    @wraps(f)
    def wrapper(*args, **kwargs):
        moves = f(*args, **kwargs)
        return {move for move in moves if _check_range(move)} - {args}

    return wrapper


def _filter_line(f):
    """
       Wraps move functions from piece.
       Gets all the possible moves and checks if they are on the same line.
       Then it removes all points not in range (bigger than end).
       Works for rook and bishop
    @param f:
    @return:
    """

    @wraps(f)
    def wrapper(*args, **kwargs):
        moves = f(*args, **kwargs)
        # get start/end points from object
        start, end = args[0].position, args[1]
        # get the line formula as a callable
        in_line = _line(end, start=start)
        # calculate the diff of start and end
        diff = _diff_points(start, end)
        # make sure the point is bigger than start and smaller than end
        # start 3,3 end 5,5 -> 2,2 is not bigger than start 6,6 is not bigger
        # than end
        start_check = lambda _move: _diff_points(start, _move) == diff
        end_check = _end_point_check(diff)
        moves = {move for move in moves
                 if in_line(*move) and start_check(move) and end_check(move, end)
        }
        return moves

    return wrapper


def _check_blocks(f):
    @wraps(f)
    def wrapper(*args, **kwargs):
        moves = f(*args, **kwargs)
        if not moves:
            return False
        piece, end, board = args[0], args[1], args[2]
        # check if no items block the way
        if len({i for i in moves if board[i] is None}) not in (len(moves), len(moves) - 1):
            return False
        else:
            return moves

    return wrapper


def _check_move_found(f):
    @wraps(f)
    def wrapper(*args, **kwargs):
        moves = f(*args, **kwargs)
        piece, end, board = args[0], args[1], args[2]
        item_at_end = board[end]
        if not moves:
            return False
        if end not in moves:
            return False
        if item_at_end is not None and piece.color is item_at_end.color:
            return False
        return moves

    return wrapper


class Piece(object):
    __metaclass__ = ABCMeta

    def __init__(self, color: str, position: tuple):
        self.color = color
        self.position = position

    def move(self, end: tuple, board: OrderedDict):
        board[self.position] = None
        self.position = end
        board[end] = self

    @abstractmethod
    def find(self, x: int, y: int):
        pass

    @abstractmethod
    def check_move(self, end: tuple, board: OrderedDict):
        pass

    def __repr__(self):
        return "%s %s " % (self.color, type(self).__name__,)

    def __str__(self):
        return "%s %s" % (repr(self), str(self.position))


class Rook(Piece):

    @_clean_moves
    def find(self, x: int, y: int) -> set:
        return {(x, i) for i in range(0, 8)}.union({(i, y) for i in range(0, 8)})

    @_check_move_found
    @_check_blocks
    @_filter_line
    def check_move(self, end: tuple, board: OrderedDict):
        return self.find(*self.position)


class Bishop(Piece):

    @_clean_moves
    def find(self, x: int, y: int) -> set:
        possible = lambda k: [
            (x + k, y + k), (x + k, y - k), (x - k, y + k), (x - k, y - k)]
        return {j for i in range(1, 8) for j in possible(i)}

    @_check_move_found
    @_check_blocks
    @_filter_line
    def check_move(self, end: tuple, board: OrderedDict):
        return self.find(*self.position)


class Knight(Piece):

    @_clean_moves
    def find(self, x: int, y: int) -> set:
        moves = chain(product([x - 1, x + 1], [y - 2, y + 2]),
                      product([x - 2, x + 2], [y - 1, y + 1]))
        return set(moves)

    @_check_move_found
    def check_move(self, end: tuple, board: OrderedDict):
        return self.find(*self.position)


class Pawn(Piece):

    def __init__(self, color: str, position: tuple):
        super(Pawn, self).__init__(color, position)
        self.y_initial, self.y_add = (6, -1) if self.color == game.player_down else (1, 1)

    @_clean_moves
    def find(self, x: int, y: int) -> set:
        # TODO en passant
        moves = {(x, y + self.y_add)}
        if y == self.y_initial:  # first position can move two
            moves.add((x, y + self.y_add * 2))
        return moves

    @_check_blocks
    @_check_move_found
    def check_move(self, end: tuple, board: OrderedDict):
        return self.find(*self.position)


class King(Piece):

    @_clean_moves
    def find(self, x: int, y: int) -> set:
        return product([x - 1, x + 1, x], [y + 1, y - 1, y])

    @_check_move_found
    def check_move(self, end: tuple, board: OrderedDict):
        return self.find(*self.position)


class Queen(Piece):

    def __init__(self, color: str, position: tuple):
        super(Queen, self).__init__(color, position)
        self._rook = Rook(color, position)
        self._bishop = Bishop(color, position)

    def _update_position(self, position):
        self.position = position
        self._rook.position = position
        self._bishop.position = position

    def find(self, x: int, y: int):
        return self._bishop.find(x, y).union(self._rook.find(x, y))

    @_filter_line
    def check_move(self, end: tuple, board: OrderedDict):
        return self.find(*self.position)

        # 0y [0, 1, 2, 3, 4, 5, 6, 7]x
        # 1y [0, 1, 2, 3, 4, 5, 6, 7]x
        # 2y [0, 1, 2, 3, 4, 5, 6, 7]x
        # 3y [0, 1, 2, 3, 4, 5, 6, 7]x
        # 4y [0, 1, 2, 3, 4, 5, 6, 7]x
        # 5y [0, 1, 2, 3, 4, 5, 6, 7]x
        # 6y [0, 1, 2, 3, 4, 5, 6, 7]x
        # 7y [0, 1, 2, 3, 4, 5, 6, 7]x
