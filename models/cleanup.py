from odoo import models, _

class RecordCleanup(models.AbstractModel):
    _name = 'universal_data_import.record_cleanup'
    _description = 'Universal Record Cleanup'
    
    def cleanup_unused_records(
        self,
        model_name,
        protected_sources=None,
        batch_size=300,
    ):
        Records = self.env[model_name].sudo()
    
        protected_ids = set()
    
        if protected_sources:
            for source_model, source_field in protected_sources:
                records = (
                    self.env[source_model]
                    .sudo()
                    .with_context(active_test=False)
                    .search([])
                )
    
                protected_ids.update(
                    records.mapped(source_field).ids
                )
    
        domain = []
    
        if protected_ids:
            domain.append(('id', 'not in', list(protected_ids)))
    
        records = Records.search(
            domain,
            order='id',
            limit=batch_size,
        )
    
        if not records:
            return {
                'completed': True,
                'type': 'ir.actions.client',
                'tag': 'display_notification',
                'params': {
                    'title': _('Completed'),
                    'message': _('There are no more records to delete.'),
                    'type': 'warning',
                    'sticky': False,
                }
            }
    
        deleted_count = len(records)
        records.unlink()
    
        return {
            'completed': False,
            'type': 'ir.actions.client',
            'tag': 'display_notification',
            'params': {
                'title': _('Batch Complete'),
                'message': _(
                    '%s records have been deleted. '
                    'Run the action again to process the next batch.'
                ) % deleted_count,
                'type': 'success',
                'sticky': False,
            }
        }