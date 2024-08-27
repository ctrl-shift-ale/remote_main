resource "aws_secretsmanager_secret" "db_credentials_" {
  name_prefix = "totesys-credentials-"
}
/*
resource "aws_secretsmanager_secret" "dw_credentials_" {
  name_prefix = "totesys-data-warehouse-credentials-"
}
*/
resource "aws_secretsmanager_secret_version" "db_credentials_" {
  secret_id     = aws_secretsmanager_secret.db_credentials_.id
  secret_string = jsonencode({
    user = var.DB_UN
    password = var.DB_PW
    host     = var.DB_HT
    database = var.DB_NAME
    port     = var.DB_PT
  })

  depends_on = [aws_secretsmanager_secret.db_credentials_]
}

/*
resource "aws_secretsmanager_secret_version" "dw_credentials_" {
  secret_id     = aws_secretsmanager_secret.dw_credentials_.id
  secret_string = jsonencode({
    DB_USERNAME = var.DW_UN
    DB_PASSWORD = var.DW_PW
    DB_NAME     = var.DW_DB
    DB_HOST     = var.DW_HT
    DB_PORT     = var.DW_PT
  })

  depends_on = [aws_secretsmanager_secret.dw_credentials_]
}
*/