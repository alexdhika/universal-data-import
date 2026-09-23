from odoo import models, fields, api, _
from odoo.exceptions import ValidationError, UserError
import traceback
import inspect

class ImportTypes(models.Model):
    _name = 'universal_data_import.import_types'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _description = 'Import Types Mixin'

    name = fields.Char(string='Name', required=True)
    sequence = fields.Integer(
        string='Sequence',
        default=10,
    )
    operation_type = fields.Selection([
        ('delete', 'Delete'),
        ('create', 'Create'),
        ('update', 'Update'),
        ('validate', 'Validate'),
    ], string='Operation Type',
    required=True,
    group_expand='_group_expand_operation_type')

    prefix_method = fields.Char(string='Prefix Method',
        required=True,
        help="Prefix method digunakan untuk menentukan method yang akan dieksekusi. Method yang akan dieksekusi harus memiliki nama dengan format: action_<operation_type>_<prefix_method>")

    @api.onchange('prefix_method')
    def _onchange_prefix_method(self):
        if self.prefix_method:
            self.prefix_method = self.prefix_method.lower().replace(' ', '')

    _sql_constraints = [
        ('uniq_prefix_method', 'unique(operation_type, prefix_method)', 'The combination of operation type and prefix method must be unique.'),
    ]

    prefix_method_action = fields.Char(
        string='Prefix Method',
        compute='_generate_prefix_method_action'
    )

    def _generate_prefix_method_action(self):
        for record in self:
            if record.operation_type and record.prefix_method:
                record.prefix_method_action = (
                    f'action_{record.operation_type}_{record.prefix_method}*'
                )
            else:
                record.prefix_method_action = False

    data_source_id = fields.Many2one(
            'universal_data_import.data_source_config', 
            string='Data Source'
        )

    # buatkan field one2many untuk menampung method_list
    # yang berisi nama method, tanggal terakhir eksekusi, dan status terakhir eksekusi
    method_list_ids = fields.One2many('universal_data_import.method_list', 'import_type_id', string='Method List')

    @api.model
    def _group_expand_operation_type(self, groups, domain, order):
        return [
            'delete',
            'create',
            'update',
            'validate'
        ]

    def generate_method_list(self):
        prefix_method = f"action_{self.operation_type}_{self.prefix_method}"
        existing_methods = set(self.method_list_ids.mapped('name'))
        method_list = []
        
        target_inherit = 'universal_data_import.import_types'
    
        # Filter model yang terdaftar di registry saja
        for model in self.env['ir.model'].search([]):
            if model.model not in self.env.registry:
                continue
    
            model_obj = self.env[model.model]
            
            # 1. Normalisasi _inherit menjadi set/list (karena _inherit bisa bertipe str atau list/tuple)
            raw_inherit = getattr(model_obj, '_inherit', [])
            if isinstance(raw_inherit, str):
                inherit_models = [raw_inherit]
            else:
                inherit_models = list(raw_inherit) if raw_inherit else []
    
            model_real_name = model_obj._name
    
            # 2. Cek apakah model ini adalah target ATAU meng-inherit target (langsung / via MRO)
            # Menggunakan _parents_data atau MRO registry Odoo agar inheritance bertingkat tetap terdeteksi
            is_target_model = (
                model_real_name == target_inherit
                or target_inherit in inherit_models
                or target_inherit in getattr(model_obj, '_parents_data', {})
            )
    
            if is_target_model:
                for method_name in dir(model_obj):
                    if (
                        method_name.startswith(prefix_method)
                        and method_name not in existing_methods
                    ):
                        method_list.append((0, 0, {
                            'name': method_name,
                            'model_id': model.id,
                            'last_execution_date': False,
                            'last_execution_status': 'pending',
                        }))
                        
                        # Tambahkan ke set agar tidak duplikat
                        existing_methods.add(method_name)
    
        if method_list:
            self.write({
                'method_list_ids': method_list
            })
            
    def generate_method_list1(self):
        prefix_method = 'action_' + self.operation_type + '_' + self.prefix_method
        # Method yang sudah ada
        existing_methods = set(self.method_list_ids.mapped('name'))
        method_list = []
        
        for model in self.env['ir.model'].search([]):

            if model.model not in self.env.registry:
                continue

            model_obj = self.env[model.model]
            inherit_models = model_obj._inherit
            model_real_name = model_obj._name

            if (
                model_real_name == 'universal_data_import.import_types'
                or 'universal_data_import.import_types' in inherit_models
            ):

                for method_name in dir(model_obj):

                    if (
                        method_name.startswith(prefix_method)
                        and method_name not in existing_methods
                    ):
                        method_list.append((0, 0, {
                            'name': method_name,
                            'model_id': model.id,
                            'last_execution_date': False,
                            'last_execution_status': 'pending',
                        }))

                        # Supaya tidak kembar jika ditemukan lagi
                        existing_methods.add(method_name)

        if method_list:
            self.write({
                'method_list_ids': method_list
            })

    def execute_all_methods(self):
        messages = []

        for method in self.method_list_ids:
            result = method.execute_method()

            if result and result.get('tag') == 'display_notification':
                params = result.get('params', {})
                messages.append(params.get('message', ''))

        return {
            'type': 'ir.actions.client',
            'tag': 'display_notification',
            'params': {
                'title': _('Hasil Eksekusi'),
                'message': '\n'.join(messages),
                'type': 'success',
                'sticky': True,
            }
        }

    def write(self, vals):
        if 'operation_type' in vals:
            for record in self:
                if vals['operation_type'] != record.operation_type:
                    raise UserError(
                        _('Record tidak boleh dipindahkan ke Operation Type lain.')
                    )

        return super().write(vals)

    def execute_background_method(self):
        MethodList = self.env['universal_data_import.method_list'].sudo()
    
        operation_order = {
            'delete': 1,
            'create': 2,
            'update': 3,
            'validate': 4,
        }
    
        import_types = self.env['universal_data_import.import_types'].sudo().search(
            [
                ('operation_type', 'in', list(operation_order.keys())),
            ],
            order='sequence asc, id asc'
        )
    
        import_types = import_types.sorted(
            key=lambda r: (
                operation_order.get(r.operation_type, 99),
                r.sequence,
                r.id,
            )
        )
    
        for import_type in import_types:
    
            methods = MethodList.search([
                ('import_type_id', '=', import_type.id),
                ('run_in_background', '=', True),
                ('is_completed', '=', False),
            ], order='sequence asc, id asc')
    
            # Tidak ada proses background yang belum selesai
            if not methods:
                continue
    
            # Ambil method sequence paling kecil yang belum selesai
            method = methods[0]
    
            method.execute_method()
    
            self.env.cr.commit()
    
            # Hanya satu method setiap cron berjalan
            return True
    
        return False
        
    def execute_background_method1(self, operation_type):
        MethodList = self.env['universal_data_import.method_list'].sudo()

        method = MethodList.search([
            ('run_in_background', '=', True),
            ('is_completed', '=', False),
            ('import_type_id.operation_type', '=', operation_type),
            ('last_execution_date', '=', False),
        ], order='id asc', limit=1)

        if not method:
            method = MethodList.search([
                ('run_in_background', '=', True),
                ('is_completed', '=', False),
                ('import_type_id.operation_type', '=', operation_type),
            ], order='last_execution_date asc, id asc', limit=1)

        if not method:
            return False

        method.execute_method()

        self.env.cr.commit()

        return True

    completed_status = fields.Html(
        string='Completed Status',
        compute='_compute_completed_status',
        sanitize=False,  # Agar style/class HTML FontAwesome tidak di-strip oleh Odoo
    )

    @api.depends('method_list_ids.is_completed')
    def _compute_completed_status(self):
        for record in self:
            methods = record.method_list_ids
            if not methods:
                # Kondisi jika belum ada method list
                record.completed_status = (
                    '<span class="badge badge-secondary" style="font-size: 13px; padding: 6px 10px;">'
                    '<i class="fa fa-minus-circle mr-1"></i> No Methods'
                    '</span>'
                )
                continue

            # Cek apakah semua method sudah completed
            all_completed = all(m.is_completed for m in methods)
            
            if all_completed:
                # Status Complete (Centang Hijau FA4)
                record.completed_status = (
                    '<span class="badge badge-success" style="font-size: 13px; padding: 6px 10px; color: #ffffff; background-color: #28a745;">'
                    '<i class="fa fa-check-circle mr-1"></i> Completed'
                    '</span>'
                )
            else:
                # Hitung progress jika sebagian belum selesai (Spinner / Warning FA4)
                total = len(methods)
                completed_count = sum(1 for m in methods if m.is_completed)
                
                record.completed_status = f'''
                    <span class="badge badge-warning" style="font-size: 13px; padding: 6px 10px; color: #212529; background-color: #ffc107;">
                        <i class="fa fa-spinner fa-spin mr-1"></i> In Progress ({completed_count}/{total})
                    </span>
                '''

                
class MethodList(models.Model):
    _name = 'universal_data_import.method_list'
    _description = 'Method List'

    name = fields.Char(string='Method Name', required=True)
    sequence = fields.Integer(string='Sequence', default=10)
    import_type_id = fields.Many2one('universal_data_import.import_types', string='Import Type', ondelete='cascade')
    model_id = fields.Many2one('ir.model', string='Model', required=True, ondelete='cascade')
    last_execution_date = fields.Datetime(string='Last Execution Date')
    last_execution_status = fields.Selection([
        ('success', 'Success'),
        ('failed', 'Failed'),
        ('pending', 'Pending'),
    ], string='Last Execution Status')

    error_log = fields.Text(string='Error Log', readonly=True)
    run_in_background = fields.Boolean(string='Run In Background')
    is_completed = fields.Boolean(
        string='Completed',
        readonly=True)

    last_execution_relative = fields.Char(
        compute='_compute_last_execution_relative'
    )

    def _compute_last_execution_relative(self):
        now = fields.Datetime.now()

        for record in self:
            if not record.last_execution_date:
                record.last_execution_relative = '-'
                continue

            diff = now - record.last_execution_date

            seconds = int(diff.total_seconds())

            if seconds < 60:
                record.last_execution_relative = f'{seconds} detik yang lalu'
            elif seconds < 3600:
                minutes = seconds // 60
                record.last_execution_relative = f'{minutes} menit yang lalu'
            elif seconds < 86400:
                hours = seconds // 3600
                record.last_execution_relative = f'{hours} jam yang lalu'
            else:
                days = seconds // 86400
                record.last_execution_relative = f'{days} hari yang lalu'

    color = fields.Integer(
            string='Color',
            compute='_compute_color'
        )

    def _compute_color(self):
        for record in self:
            if record.last_execution_status == 'success':
                record.color = 10
            elif record.last_execution_status == 'failed':
                record.color = 1
            elif record.last_execution_status == 'pending':
                record.color = 3
            else:
                record.color = 0

            if record.is_completed:
                record.color = 7

    _sql_constraints = [
        ('uniq_method_name', 'unique(import_type_id, name)', 'The method name must be unique within each import type.'),
    ]

    def execute_method(self):
        method_name = self.name
        model_name = self.model_id.model
        model_class = self.env[model_name]

        method = getattr(model_class, method_name, None)

        if not method:
            self.last_execution_date = fields.Datetime.now()
            self.last_execution_status = 'failed'
            self.error_log = (
                f'Method {method_name} not found in model {model_name}'
            )
            return False

        try:
            # Apakah method meminta parameter `method_list_rec`?
            sig = inspect.signature(method)
            
            if 'method_list_rec' in sig.parameters:
                # Jika method PUNYA parameter `method_list_rec`
                result = method(method_list_rec=self)
            else:
                # Jika method TIDAK PUNYA parameter (method biasa)
                result = method()

            self.last_execution_date = fields.Datetime.now()
            self.last_execution_status = 'success'
            self.error_log = False
            # menulis di chatter di parent (import_type_id)
            self.import_type_id.message_post(
                body=f'Success: Dieksekusi oleh {self.env.user.name}',
            )

            if isinstance(result, dict) and result.get('completed'):
                self.is_completed = True

            return result

        except Exception:
            self.last_execution_date = fields.Datetime.now()
            self.last_execution_status = 'failed'
            self.error_log = traceback.format_exc()
            # menulis di chatter di parent (import_type_id)
            self.import_type_id.message_post(
                body=f'Error: Dieksekusi oleh {self.env.user.name}',
            )
            return False
