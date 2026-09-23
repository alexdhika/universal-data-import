# Odoo Universal Data Import

Universal Data Import is an Odoo addon designed to simplify data ingestion from multiple external sources into Odoo. It supports imports from APIs, databases, and uploaded files, and allows administrators to define reusable import operations using method-based execution patterns.

## Overview

This project provides a flexible import framework for organizations that need to synchronize or migrate data from external systems into Odoo models. Instead of writing one-off scripts for every data source, the module centralizes connection configuration and import logic into reusable Odoo records.

The addon is especially useful when you need to:

- connect to remote APIs and fetch source data
- import data from relational databases
- process uploaded files such as CSV, XLSX, or other structured formats
- organize import logic by operation type such as create, update, delete, and validate
- track execution history and logs for each import method

## Features

- Multiple source types:
  - API
  - Database
  - File upload
- Connection testing from the Odoo UI
- Dynamic method discovery based on operation type and prefix
- Background execution support for import jobs
- Execution status tracking and error logging
- Integration with Odoo mail chatter for activity tracking
- Configurable authentication and request parameters

## Supported Source Types

### 1. API Source

Connect to external HTTP services using:

- Basic Authentication
- Token Authentication
- OAuth 2.0-style configuration
- Custom headers and parameters
- Request timeout configuration

### 2. Database Source

Connect to common database engines, including:

- PostgreSQL
- MySQL
- SQLite
- Oracle
- Microsoft SQL Server

The configuration supports either a full database URI or a driver-based connection setup.

### 3. File Source

Upload a file directly into Odoo and process it with the import workflow. This is useful for CSV-style or spreadsheet-based data ingestion.

## Installation

1. Copy the module into your Odoo custom addons directory.
2. Update the Odoo addons path if needed.
3. Restart the Odoo server.
4. Update the app list in Odoo.
5. Install the module named Universal Data Import.

### Dependencies

The module depends on the standard Odoo base and mail apps. For database connectivity, the Python environment must also include the required database drivers and libraries, such as SQLAlchemy.

## Configuration

After installation, the module is available from the Odoo menu:

- Data Import
  - Dashboard
  - Configuration
    - Data Sources

### Data Source Configuration

Create a data source record and set the required fields according to the selected source type:

- API: endpoint, headers, authentication, timeout
- Database: URI or driver details, credentials, database name
- File: uploaded binary file and filename

Use the Test Connection action to verify connectivity before running import operations.

## Import Type Workflow

The import framework organizes operations using import types and method names that follow a naming convention.

A method should follow this pattern:

- action_delete_<prefix>
- action_create_<prefix>
- action_update_<prefix>
- action_validate_<prefix>

Example:

```python
def action_create_customer(self, method_list_rec=False):
    # Import logic here
    return {
        'completed': True,
    }
```

In the Odoo UI, an import type can be configured with:

- operation type
- prefix method
- related data source
- generated method list
- execution status for each method

The module automatically discovers methods matching the configured pattern and adds them to the import method list.

## Execution and Monitoring

Each method can be:

- executed manually
- executed in a background job
- tracked with its last execution date and status
- reviewed with detailed error logs

This makes it easier to monitor successful imports and investigate failures.

## Project Structure

```text
universal_data_import/
├── __init__.py
├── __manifest__.py
├── README.md
├── LICENSE
├── data/
│   └── ir_cron.xml
├── models/
│   ├── __init__.py
│   ├── cleanup.py
│   ├── config.py
│   └── import_types.py
├── security/
│   └── ir.model.access.csv
├── static/
│   └── description/
├── views/
│   ├── data_source_config_views.xml
│   ├── import_types_views.xml
│   └── menu.xml
└── __pycache__/
```

## Notes

This addon is intended as a reusable framework for import workflows. Depending on your business needs, you can extend it with custom import methods to map external data into Odoo records, validate fields, or trigger downstream processes.

## License

This project is distributed under the license declared in the repository's LICENSE file.
