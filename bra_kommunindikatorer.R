
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

  # hämta Python-skript från Github och spara i en tillfällig mapp för att kunna anropa från system2()
  py_url <- "https://raw.githubusercontent.com/Analytikernatverket/hamta_data_playwright/main/bra_kommunindikatorer.py"
  py_temp <- tempfile(fileext = ".py")
  py_resp <- GET(py_url)
  stop_for_status(py_resp)
  writeBin(httr::content(py_resp, "raw"), py_temp)
  
  # kör python-scriptet
  system2("python", c(py_temp, py_mapp, valda_kommuner))
  
  xlsx_fillista <- list.files(py_mapp, full.names = TRUE, pattern = "\\.xlsx$")
  filnamn <- basename(xlsx_fillista) 
  
  bra_xlsx_list <- xlsx_fillista %>% 
    set_names(basename(xlsx_fillista) %>% str_remove(".xlsx")) %>% 
    map(function(fil) {
    flikar <- excel_sheets(fil)
    suppressMessages(
      map(set_names(flikar), ~ readxl::read_xlsx(fil, sheet = .x, col_names = FALSE)))
  }, .progress = TRUE) 
 
  las_in_data_fran_flik <- function(fil, fliknamn){
    
    # läs in om det är en anmälda brott-flik ===============================================================================
    if (str_detect(fliknamn, "(anmälda)")){
      
      # läs in data
      anmalda_data <- fil[[fliknamn]]
      innehall <- anmalda_data[[1,1]]
      
      anmalda_data[[2,1]] <- "geografi"
      kolumn_namn <- slice(anmalda_data, 2) %>% as.character()
      anmalda_data <- anmalda_data %>% slice(3:nrow(anmalda_data))
      names(anmalda_data) <- kolumn_namn
      
      anmalda_data_long <- anmalda_data %>%
        pivot_longer(
          cols = -geografi,
          names_to = c("enhet", "ar"),
          names_pattern = "^(.*) (\\d{4})$",
          values_to = "varde"
        ) %>% 
        mutate(kalla = "Anmälda brott",
               varde = varde %>% as.numeric(),
               variabel = innehall %>% 
                 str_remove(" i kommunen, länet.*") %>%
                 str_remove(fixed("(anmälda brott)")) %>% 
                 str_trim()
               ) %>% 
        relocate(variabel, .after = ar)
      
      return(anmalda_data_long)
    } # slut if-sats för om det är en anmälda brott-flik
    
    # läs in om det är en NTU-flik, eller otrygghets-flikar ===============================================================================
    #if (str_detect(fliknamn, "(NTU)")) {
    if (!str_detect(fliknamn, "(anmälda)")) {
      
      ntu_data <- fil[[fliknamn]]
      innehall <- ntu_data[[1,1]]
      
      ntu_data[[2,1]] <- "geografi"
      kolumn_namn <- slice(ntu_data, 2) %>% as.character()
      ntu_data <- ntu_data %>% slice(3:nrow(ntu_data))
      names(ntu_data) <- kolumn_namn
      
      ntu_data_long <- ntu_data %>%
        pivot_longer(
          cols = -geografi,
          names_to = "ar",
          values_to = "varde"
        ) %>% 
        mutate(ar = str_extract(ar, "\\d{4}$"),
               kalla = "Nationella trygghetsundersökningen (NTU)",
               varde = varde %>% as.numeric(),
               variabel = str_remove(innehall, ", enligt NTU.*") %>% 
                 str_remove(" [0-9]{4}[-–][0-9]{4}"),
               enhet = str_extract(innehall, "(?<=NTU [0-9]{4}[-–][0-9]{4}\\. ).*$")) %>% 
        relocate(variabel, .after = ar)
      
      return(ntu_data_long)
    } # slut if-sats för om det är en NTU-flik
    
  } # slut funktion för att hämta data i en flik
  
  dataset_bra <- map(bra_xlsx_list, function(fil) {
    map(names(fil), ~ las_in_data_fran_flik(fil = fil, fliknamn = .x)) %>% 
      list_rbind()      # bind ihop alla flikar till en dataframe
  }) %>% 
    list_rbind() %>%    # bind ihop alla excelfiler till en dataframe
    distinct()
  
  return(dataset_bra)
}