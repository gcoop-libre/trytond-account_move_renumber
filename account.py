# The COPYRIGHT file at the top level of this repository contains the full
# copyright notices and license terms.
from trytond.model import ModelView, fields
from trytond.pool import Pool, PoolMeta
from trytond.pyson import PYSONEncoder
from trytond.transaction import Transaction
from trytond.wizard import Wizard, StateView, StateAction, Button

__all__ = ['Move', 'RenumberMoves', 'RenumberMovesStart']
__metaclass__ = PoolMeta


class Move:
    __name__ = 'account.move'

    @classmethod
    def write(cls, *args):
        remove_post_number = False
        if (Transaction().context.get('account_move_renumber')
                and 'post_number' not in cls._check_modify_exclude):
            cls._check_modify_exclude.append('post_number')
            remove_post_number = True

        super(Move, cls).write(*args)

        if remove_post_number:
            cls._check_modify_exclude.remove('post_number')


class RenumberMovesStart(ModelView):
    '''Renumber Account Moves Start'''
    __name__ = 'account.move.renumber.start'

    fiscalyear = fields.Many2One('account.fiscalyear', 'Fiscal Year',
        required=True)
    first_number = fields.Integer('First Number', required=True,
        domain=[('first_number', '>', 0)])

    @staticmethod
    def default_first_number():
        return 1


class RenumberMoves(Wizard):
    '''Renumber Account Moves'''
    __name__ = 'account.move.renumber'

    start = StateView('account.move.renumber.start',
        'account_move_renumber.move_renumber_start_view_form', [
            Button('Cancel', 'end', 'tryton-cancel'),
            Button('Renumber', 'renumber', 'tryton-ok', default=True),
            ])
    renumber = StateAction('account.act_move_form')

    @classmethod
    def __setup__(cls):
        super(RenumberMoves, cls).__setup__()
        cls._error_messages.update({
                'draft_moves_in_fiscalyear': (
                    'There are Draft Moves in Fiscal Year "%(fiscalyear)s".'),
                })

    def do_renumber(self, action):
        pool = Pool()
        Move = pool.get('account.move')
        Sequence = pool.get('ir.sequence')

        draft_moves = Move.search([
                ('period.fiscalyear', '=', self.start.fiscalyear.id),
                ('state', '=', 'draft'),
                ])
        if draft_moves:
            self.raise_user_warning('move_renumber_draft_moves%s'
                    % self.start.fiscalyear.id,
                'draft_moves_in_fiscalyear', {
                    'fiscalyear': self.start.fiscalyear.rec_name,
                    })

        sequences = set([self.start.fiscalyear.post_move_sequence])
        for period in self.start.fiscalyear.periods:
            sequences.add(period.post_move_sequence)

        Sequence.write(list(sequences), {
                'number_next': self.start.first_number,
                })

        moves_to_renumber = Move.search([
                ('period.fiscalyear', '=', self.start.fiscalyear.id),
                ('post_number', '!=', None),
                ],
            order=[
                ('post_date', 'ASC'),
                ('id', 'ASC'),
                ])
        move_vals = []
        for move in moves_to_renumber:
            move_vals.extend(([move], {
                        'post_number': Sequence.get_id(
                            move.period.post_move_sequence_used.id),
                        }))
        with Transaction().set_context(account_move_renumber=True):
            Move.write(*move_vals)

        action['pyson_domain'] = PYSONEncoder().encode([
            ('period.fiscalyear', '=', self.start.fiscalyear.id),
            ('post_number', '!=', None),
            ])
        return action, {}

    def transition_renumber(self):
        return 'end'
