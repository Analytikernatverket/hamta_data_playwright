hamta_nationella_emissionsdatabasen <- function(
    hamta_excelfil = TRUE,
    hamta_gislager = FALSE,
    filtrera_lan = NA, 
    filtrera_kommuner = NA,
    huvudsektor = "Transporter",
    undersektor = NA,
    amne = "Växthusgaser totalt",
    python = "python",
    script_path = "C:/Lokalt/hamta_smhi.py"
) {
  if (!require("pacman")) install.packages("pacman")
  pacman::p_load(tidyverse, glue, readxl)
  
  retur_list <- list()
  
  if (hamta_excelfil) {
    tmpdir <- tempfile("smhi_download_")
    dir.create(tmpdir)
    
    # kör python-scriptet
    args <- c(script_path, tmpdir,
              ifelse(is.na(huvudsektor), "NA", huvudsektor))
    system2(python, args)
    
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
    
    data_list <- list(data_long)
    names(data_list) <- basename(xlsx_file) %>% str_remove("\\.xlsx$") %>% paste0("_excel")
    
    retur_list <- c(retur_list, data_list)
    unlink(tmpdir, recursive = TRUE, force = TRUE)
  }
  
  return(retur_list)
}
