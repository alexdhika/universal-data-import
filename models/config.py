import base64
import io
import json
import requests
import urllib.parse
from odoo import models, fields, api, _
from odoo.exceptions import ValidationError, UserError
from sqlalchemy import create_engine
from sqlalchemy.engine import URL

class DataSourceConfig(models.Model):
    _name = 'universal_data_import.data_source_config'
    _description = 'Data Source Configuration'

    name = fields.Char(string='Name', required=True)
    source_type = fields.Selection([
        ('api', 'API'),
        ('database', 'Database'),
        ('file', 'File')
    ], string='Source Type', required=True)
    api_endpoint = fields.Char(string='API Endpoint')
    database_uri = fields.Char(string='Database URI')
    file = fields.Binary(string='File')
    file_filename = fields.Char(string='File Name')

    @api.constrains('source_type', 'api_endpoint', 'database_uri', 'file')
    def _check_source_configuration(self):
        for record in self:
            if record.source_type == 'api' and not record.api_endpoint:
                raise ValidationError(_('API Endpoint is required for API source type.'))
            elif record.source_type == 'database' and not record.database_uri:
                raise ValidationError(_('Database URI is required for Database source type.'))
            elif record.source_type == 'file' and not record.file:
                raise ValidationError(_('File is required for File source type.'))

    api_key = fields.Char(string='API Key')
    api_secret = fields.Char(string='API Secret')
    api_token = fields.Char(string='API Token')
    api_version = fields.Char(string='API Version')
    api_timeout = fields.Integer(string='API Timeout (seconds)', default=30)
    api_headers = fields.Text(string='API Headers (JSON format)', help="Provide additional headers in JSON format for API requests.")
    api_params = fields.Text(string='API Parameters (JSON format)', help="Provide additional parameters in JSON format for API requests.")
    api_auth_method = fields.Selection([
        ('basic', 'Basic Authentication'),
        ('token', 'Token Authentication'),
        ('oauth2', 'OAuth 2.0')
    ], string='API Authentication Method', default='basic')

    database_driver = fields.Selection([
        ('postgresql', 'PostgreSQL'),
        ('mysql', 'MySQL'),
        ('sqlite', 'SQLite'),
        ('oracle', 'Oracle'),
        ('mssql', 'Microsoft SQL Server')
    ], string='Database Driver')
    database_name = fields.Char(string='Database Name')
    database_user = fields.Char(string='Database User')
    database_password = fields.Char(string='Database Password')

    @api.constrains('source_type', 'api_endpoint', 'database_uri', 'file')
    def _check_source_configuration(self):
        for record in self:
            if record.source_type == 'api' and not record.api_endpoint:
                raise ValidationError(_('API Endpoint is required for API source type.'))
            elif record.source_type == 'database' and not record.database_uri:
                raise ValidationError(_('Database URI is required for Database source type.'))
            elif record.source_type == 'file' and not record.file:
                raise ValidationError(_('File is required for File source type.'))

    # ==================== METHOD KONEKSI ==================== #

    def get_connection(self, **kwargs):
        """
        Method generik untuk mendapatkan objek koneksi atau data stream.
        - API: Mengembalikan requests.Session
        - Database: Mengembalikan sqlalchemy.engine.Engine
        - File: Mengembalikan file-like object (BytesIO) / Pandas DataFrame
        """
        self.ensure_one()
        try:
            if self.source_type == 'api':
                return self._get_api_connection(**kwargs)
            elif self.source_type == 'database':
                return self._get_database_connection(**kwargs)
            elif self.source_type == 'file':
                return self._get_file_connection(**kwargs)
        except Exception as e:
            raise UserError(_("Koneksi ke '%s' gagal: %s") % (self.name, str(e)))

    def _get_api_connection(self, **kwargs):
        """Membentuk requests.Session lengkap dengan auth dan header"""
        session = requests.Session()
        
        # Headers
        headers = {}
        if self.api_headers:
            headers = json.loads(self.api_headers)
        session.headers.update(headers)

        # Authentication
        if self.api_auth_method == 'basic' and self.api_key:
            session.auth = (self.api_key, self.api_secret or '')
        elif self.api_auth_method == 'token' and self.api_token:
            session.headers.update({'Authorization': f'Bearer {self.api_token}'})

        return session

    def _get_database_connection(self, **kwargs):
        """Membentuk SQLAlchemy Engine khusus untuk 5 Database Engine"""
        try:
            from sqlalchemy import create_engine
        except ImportError:
            raise UserError(_("Library 'sqlalchemy' belum di-install di server."))
    
        db_uri = (self.database_uri or '').strip()
        timeout = self.api_timeout or 30
    
        # 1. BILA PENGGUNA MEMASUKKAN FULL URI (Mengandung '://')
        if '://' in db_uri:
            # Menambahkan timeout koneksi secara generik
            return create_engine(db_uri, connect_args={'timeout': timeout} if 'sqlite' in db_uri else {})
    
        if not self.database_driver:
            raise UserError(_("Pilih 'Database Driver' atau isi 'Database URI' secara lengkap."))
    
        host = db_uri if db_uri else 'localhost'
        user = urllib.parse.quote_plus(self.database_user or '')
        password = urllib.parse.quote_plus(self.database_password or '')
        dbname = self.database_name or ''
        driver = self.database_driver
    
        connect_args = {}
    
        # --- CASE 1: POSTGRESQL ---
        if driver == 'postgresql':
            final_uri = f"postgresql+psycopg2://{user}:{password}@{host}/{dbname}"
            connect_args = {'connect_timeout': timeout}
    
        # --- CASE 2: MYSQL ---
        elif driver == 'mysql':
            final_uri = f"mysql+pymysql://{user}:{password}@{host}/{dbname}"
            connect_args = {'connect_timeout': timeout}
    
        # --- CASE 3: SQLITE ---
        elif driver == 'sqlite':
            file_path = dbname or host
            final_uri = f"sqlite:///{file_path}"
            connect_args = {'timeout': timeout}
    
        # --- CASE 4: ORACLE ---
        elif driver == 'oracle':
            final_uri = f"oracle+cx_oracle://{user}:{password}@{host}/{dbname}"
    
        # --- CASE 5: MICROSOFT SQL SERVER (MSSQL) ---
        elif driver == 'mssql':
            odbc_driver = urllib.parse.quote_plus('ODBC Driver 17 for SQL Server')
            final_uri = f"mssql+pyodbc://{user}:{password}@{host}/{dbname}?driver={odbc_driver}"
            # PyODBC menggunakan parameter 'timeout' di connect_args
            connect_args = {'timeout': timeout}
    
        else:
            raise UserError(_("Database driver '%s' tidak didukung.") % driver)
    
        # PERBAIKAN: Hapus 'timeout=...' dari create_engine() dan gunakan 'connect_args'
        return create_engine(final_uri, connect_args=connect_args)

    def _get_file_connection(self, **kwargs):
        """Mengembalikan file-like BytesIO yang siap dibaca Pandas/CSV reader"""
        if not self.file:
            raise UserError(_("File tidak ditemukan."))
            
        file_data = base64.b64decode(self.file)
        file_stream = io.BytesIO(file_data)
        file_stream.name = self.file_filename or 'import_file'
        return file_stream

    def action_test_connection(self):
        """Method untuk dipanggil dari tombol UI 'Test Connection'"""
        self.ensure_one()
        conn = self.get_connection()
        
        if self.source_type == 'api':
            params = json.loads(self.api_params) if self.api_params else {}
            response = conn.get(self.api_endpoint, params=params, timeout=self.api_timeout)
            response.raise_for_status()
            message = _("Koneksi API Berhasil! Status Code: %s") % response.status_code

        elif self.source_type == 'database':
            with conn.connect() as connection:
                message = _("Koneksi Database Berhasil!")

        elif self.source_type == 'file':
            message = _("File '%s' siap diproses!") % self.file_filename

        return {
            'type': 'ir.actions.client',
            'tag': 'display_notification',
            'params': {
                'title': _("Test Connection Success"),
                'message': message,
                'type': 'success',
                'sticky': False,
            }
        }