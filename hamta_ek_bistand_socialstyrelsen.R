
hamta_ek_bistand_socialstyrelsen <- function() {
  
  if (!require("pacman")) install.packages("pacman")
  p_load(tidyverse,
         glue,
         readxl)
  
  # skapa temporär mapp
  tmpdir <- tempfile()
  dir.create(tmpdir)
  
  # hämta Python-skript från Github och spara i en tillfällig mapp för att kunna anropa från system2()
  py_url <- "https://raw.githubusercontent.com/Analytikernatverket/hamta_data_playwright/refs/heads/main/hamta_ek_bistand_socialstyrelsen.py"
  py_temp <- tempfile(fileext = ".py")
  py_resp <- GET(py_url)
  stop_for_status(py_resp)
  writeBin(content(py_resp, "raw"), py_temp)
  
  system2("python", c(py_temp, tmpdir))
  sokvag_filnamn <- list.files(tmpdir, full.names = TRUE)
  inlasfil <- suppressMessages(read_xlsx(sokvag_filnamn, col_names = FALSE))
  
  enhet_kol <- inlasfil[[1,1]]
  kol_namn <- inlasfil[2,] %>% as.character()
  
  inlasfil <- inlasfil %>% slice(3:nrow(.)) %>% 
    setNames(kol_namn) 
  
  dataset_slutrad <- which(is.na(inlasfil[["År"]]))[1] - 1
  
  suppress_specific_warning(
  inlasfil <- inlasfil %>%
    slice(1:dataset_slutrad) %>% 
    pivot_longer(cols = c("Januari":"December"), names_to = "Månad", values_to = enhet_kol) %>% 
    mutate({{ enhet_kol }} := na_if(str_replace_all(.data[[enhet_kol]], "--", NA_character_), NA_character_),
           {{ enhet_kol }} := .data[[enhet_kol]] %>% as.numeric())
  )
  
  regionnyckel <- hamtaregtab() %>% 
    rename(Regionkod = regionkod)
  
  manadsnyckel <- tibble(
    Månad = format(ISOdate(2000, 1:12, 1), "%B") %>% str_to_sentence(),
    Månad_num = c(1:12)
  )
  
  inlasfil <- inlasfil %>% 
    left_join(regionnyckel, by = c("Region" = "region")) %>%
    relocate(Regionkod, .before = "Region") %>%
    left_join(manadsnyckel, by = "Månad") %>% 
    relocate(Månad_num, .after = "Månad")
  
  unlink(tmpdir, recursive = TRUE, force = TRUE)
  return(inlasfil)
}
