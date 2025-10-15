hamta_bra_kommunindikatorer <- function(
  region_vekt = "20"              # det går att skicka in både läns- och kommunkoder, vid länskoder så hämtas alla kommuner i länet  
  ){
  
  if (!require("pacman")) install.packages("pacman")
  pacman::p_load(tidyverse, glue, readxl)
  
  py_mapp <- file.path(tempdir(), "bra_kommunfiler")
  dir.create(py_mapp, showWarnings = FALSE, recursive = TRUE)
  
  source("https://raw.githubusercontent.com/Region-Dalarna/funktioner/main/func_API.R", encoding = "utf-8", echo = FALSE)
  
  region_vekt_kommuner <- region_vekt[nchar(region_vekt) == 4] %>% 
    hamtaregion_kod_namn() %>% 
    dplyr::pull(region)
  
  region_vekt_lan <- region_vekt[nchar(region_vekt) == 2]
  
  valda_kommuner <- hamtakommuner(region_vekt[nchar(region_vekt) == 2], F, F) %>% 
    hamtaregion_kod_namn() %>% 
    dplyr::pull(region) %>% 
    c(., region_vekt_kommuner)

  py_temp <- "G:/skript/peter/bra_kommunindikatorer_playwright.py"
  
  # hämta Python-skript från Github och spara i en tillfällig mapp för att kunna anropa från system2()
  #py_url <- "https://raw.githubusercontent.com/Analytikernatverket/hamta_data_playwright/main/hamta_emissionsdatabasen_smhi.py"
  # py_temp <- tempfile(fileext = ".py")
  # py_resp <- GET(py_url)
  # stop_for_status(py_resp)
  # writeBin(httr::content(py_resp, "raw"), py_temp)
  
  # kör python-scriptet
  system2("python", c(py_temp, py_mapp, valda_kommuner))
  
  xlsx_fillista <- list.files(py_mapp, full.names = TRUE, pattern = "\\.xlsx$")
  filnamn <- basename(xlsx_fillista) 
  
  bra_xlsx_list <- xlsx_fillista[1:3] %>% 
    set_names(basename(xlsx_fillista[1:3]) %>% str_remove(".xlsx")) %>% 
    map(function(fil) {
    flikar <- excel_sheets(fil)
    suppressMessages(
      map(set_names(flikar), ~ readxl::read_xlsx(fil, sheet = .x, col_names = FALSE)))
  }, .progress = TRUE) 
 
       
}