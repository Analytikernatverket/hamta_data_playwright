hamta_nationella_emissionsdatabasen <- function()
  {
  
  if (!require("pacman")) install.packages("pacman")
  pacman::p_load(tidyverse, glue, readxl)
  
  tmpdir <- tempfile()
  dir.create(tmpdir)
  
  # hämta Python-skript från Github och spara i en tillfällig mapp för att kunna anropa från system2()
  py_url <- "https://raw.githubusercontent.com/Analytikernatverket/hamta_data_playwright/main/hamta_emissionsdatabasen_smhi.py"
  py_temp <- tempfile(fileext = ".py")
  py_resp <- GET(py_url)
  stop_for_status(py_resp)
  writeBin(httr::content(py_resp, "raw"), py_temp)
  
  # kör python-scriptet
  system2("python", c(py_temp, tmpdir))
  
  # hitta Excel-filen i tmpdir
  xlsx_file <- list.files(tmpdir, full.names = TRUE, pattern = "\\.xlsx$")[1]
  utslapp_inlasfil <- suppressMessages(readxl::read_xlsx(xlsx_file, col_names = FALSE))
  
  # Metadata = de tre första raderna
  innehall   <- utslapp_inlasfil[2, 1, drop = TRUE]
  enhet      <- utslapp_inlasfil[3, 1, drop = TRUE]
  forklaring <- utslapp_inlasfil[4, 1, drop = TRUE]
  
  # Leta upp rubrikrad
  rubrik_rad <- which(!is.na(utslapp_inlasfil[[1]]) & seq_len(nrow(utslapp_inlasfil)) >= 5)[1]
  kolumn_namn <- as.character(utslapp_inlasfil[rubrik_rad, ])
  
  if (anyDuplicated(kolumn_namn) > 0) {
    rad_ovanfor <- as.character(utslapp_inlasfil[rubrik_rad - 1, ])
    formodligen_ar <- ifelse(is.na(rad_ovanfor), FALSE, str_detect(rad_ovanfor, "^[0-9]{4}$"))
    kolumn_namn[formodligen_ar] <- rad_ovanfor[formodligen_ar]
  }
  
  colnames(utslapp_inlasfil) <- kolumn_namn
  data <- utslapp_inlasfil[-c(1:rubrik_rad), ]
  
  data_long <- data %>%
    pivot_longer(
      cols = -(1:4),
      names_to = "År",
      values_to = "Värde"
    ) %>%
    mutate(
      Innehåll   = innehall,
      Enhet      = enhet,
      Förklaring = forklaring
    )
  
  # data_list <- list(data_long)
  # names(data_list) <- basename(xlsx_file) %>% str_remove("\\.xlsx$") %>% paste0("_excel")
  
  unlink(tmpdir, recursive = TRUE, force = TRUE)
  
  return(data_long)
}
