# The COPYRIGHT file at the top level of this repository contains the full
# copyright notices and license terms.

from trytond.pool import Pool

from . import account


def register():
    Pool.register(
        account.Move,
        account.RenumberMovesStart,
        module='account_move_renumber', type_='model')
    Pool.register(
        account.RenumberMoves,
        module='account_move_renumber', type_='wizard')
