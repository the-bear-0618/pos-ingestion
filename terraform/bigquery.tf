resource "google_bigquery_dataset" "pos_dataset" {
  project     = var.gcp_project_id
  dataset_id  = var.dataset_id
  location    = var.dataset_location
  description = "Dataset for Crown Point restaurant POS data"
}

# --- Table Resources with Final Corrected Schema Logic ---

resource "google_bigquery_table" "pos_checks" {
  project    = google_bigquery_dataset.pos_dataset.project
  dataset_id = google_bigquery_dataset.pos_dataset.dataset_id
  table_id   = "pos_checks"

  schema = jsonencode([
    for k, v in jsondecode(file("../schemas/checks.json")).properties.data.properties : {
      name = k
      # --- FIX: Explicitly set the type for the partitioning key ---
      type = k == "business_date" ? "DATE" : lookup({ "string": "STRING", "integer": "INTEGER", "number": "FLOAT64", "boolean": "BOOLEAN" }, try(v.type[0], v.type), "STRING")
      description = try(v.description, null)
      mode        = "NULLABLE"
    }
  ])
  time_partitioning {
    type  = "DAY"
    field = "business_date"
  }
}

resource "google_bigquery_table" "pos_item_sales" {
  project    = google_bigquery_dataset.pos_dataset.project
  dataset_id = google_bigquery_dataset.pos_dataset.dataset_id
  table_id   = "pos_item_sales"

  schema = jsonencode([
    for k, v in jsondecode(file("../schemas/item_sales.json")).properties.data.properties : {
      name = k
      # --- FIX: Explicitly set the type for the partitioning key ---
      type = k == "business_date" ? "DATE" : lookup({ "string": "STRING", "integer": "INTEGER", "number": "FLOAT64", "boolean": "BOOLEAN" }, try(v.type[0], v.type), "STRING")
      description = try(v.description, null)
      mode        = "NULLABLE"
    }
  ])
  time_partitioning {
    type  = "DAY"
    field = "business_date"
  }
}

resource "google_bigquery_table" "pos_time_records" {
  project    = google_bigquery_dataset.pos_dataset.project
  dataset_id = google_bigquery_dataset.pos_dataset.dataset_id
  table_id   = "pos_time_records"

  schema = jsonencode([
    for k, v in jsondecode(file("../schemas/time_records.json")).properties.data.properties : {
      name = k
      # --- FIX: Explicitly set the type for the partitioning key ---
      type = k == "business_date" ? "DATE" : lookup({ "string": "STRING", "integer": "INTEGER", "number": "FLOAT64", "boolean": "BOOLEAN" }, try(v.type[0], v.type), "STRING")
      description = try(v.description, null)
      mode        = "NULLABLE"
    }
  ])
  time_partitioning {
    type  = "DAY"
    field = "business_date"
  }
}

resource "google_bigquery_table" "pos_paidouts" {
  project    = google_bigquery_dataset.pos_dataset.project
  dataset_id = google_bigquery_dataset.pos_dataset.dataset_id
  table_id   = "pos_paidouts"

  schema = jsonencode([
    for k, v in jsondecode(file("../schemas/paidouts.json")).properties.data.properties : {
      name = k
      # --- FIX: Explicitly set the type for the partitioning key ---
      type = k == "business_date" ? "DATE" : lookup({ "string": "STRING", "integer": "INTEGER", "number": "FLOAT64", "boolean": "BOOLEAN" }, try(v.type[0], v.type), "STRING")
      description = try(v.description, null)
      mode        = "NULLABLE"
    }
  ])
  time_partitioning {
    type  = "DAY"
    field = "business_date"
  }
}

# --- Non-partitioned tables ---

resource "google_bigquery_table" "pos_customers" {
  project    = google_bigquery_dataset.pos_dataset.project
  dataset_id = google_bigquery_dataset.pos_dataset.dataset_id
  table_id   = "pos_customers"

  schema = jsonencode([
    for k, v in jsondecode(file("../schemas/customers.json")).properties.data.properties : {
      name        = k
      type        = lookup({ "string": "STRING", "integer": "INTEGER", "number": "FLOAT64", "boolean": "BOOLEAN" }, try(v.type[0], v.type), "STRING")
      description = try(v.description, null)
      mode        = "NULLABLE"
    }
  ])
}

resource "google_bigquery_table" "pos_payments" {
  project    = google_bigquery_dataset.pos_dataset.project
  dataset_id = google_bigquery_dataset.pos_dataset.dataset_id
  table_id   = "pos_payments"

  schema = jsonencode([
    for k, v in jsondecode(file("../schemas/payments.json")).properties.data.properties : {
      name        = k
      type        = lookup({ "string": "STRING", "integer": "INTEGER", "number": "FLOAT64", "boolean": "BOOLEAN" }, try(v.type[0], v.type), "STRING")
      description = try(v.description, null)
      mode        = "NULLABLE"
    }
  ])
}

resource "google_bigquery_table" "pos_item_sale_taxes" {
  project    = google_bigquery_dataset.pos_dataset.project
  dataset_id = google_bigquery_dataset.pos_dataset.dataset_id
  table_id   = "pos_item_sale_taxes"

  schema = jsonencode([
    for k, v in jsondecode(file("../schemas/item_sale_taxes.json")).properties.data.properties : {
      name        = k
      type        = lookup({ "string": "STRING", "integer": "INTEGER", "number": "FLOAT64", "boolean": "BOOLEAN" }, try(v.type[0], v.type), "STRING")
      description = try(v.description, null)
      mode        = "NULLABLE"
    }
  ])
}

resource "google_bigquery_table" "pos_item_sale_components" {
  project    = google_bigquery_dataset.pos_dataset.project
  dataset_id = google_bigquery_dataset.pos_dataset.dataset_id
  table_id   = "pos_item_sale_components"

  schema = jsonencode([
    for k, v in jsondecode(file("../schemas/item_sale_components.json")).properties.data.properties : {
      name        = k
      type        = lookup({ "string": "STRING", "integer": "INTEGER", "number": "FLOAT64", "boolean": "BOOLEAN" }, try(v.type[0], v.type), "STRING")
      description = try(v.description, null)
      mode        = "NULLABLE"
    }
  ])
}

resource "google_bigquery_table" "pos_item_sale_adjustments" {
  project    = google_bigquery_dataset.pos_dataset.project
  dataset_id = google_bigquery_dataset.pos_dataset.dataset_id
  table_id   = "pos_item_sale_adjustments"

  schema = jsonencode([
    for k, v in jsondecode(file("../schemas/item_sale_adjustments.json")).properties.data.properties : {
      name        = k
      type        = lookup({ "string": "STRING", "integer": "INTEGER", "number": "FLOAT64", "boolean": "BOOLEAN" }, try(v.type[0], v.type), "STRING")
      description = try(v.description, null)
      mode        = "NULLABLE"
    }
  ])
}