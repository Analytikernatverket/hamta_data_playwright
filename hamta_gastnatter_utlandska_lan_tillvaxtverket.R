
hamta_gastnatter_per_hemland_lan_tillvaxtverket <- function() {

  if (!require("pacman")) install.packages("pacman")
  p_load(tidyverse,
         glue,
         httr,
         readxl)

  # skapa temporär mapp
  tmpdir <- tempfile()
  dir.create(tmpdir)

  # hämta Python-skript från Github och spara i en tillfällig mapp för att kunna anropa från system2()
  py_url <- "https://raw.githubusercontent.com/Analytikernatverket/hamta_data_playwright/main/hamta_gastnatter_per_hemland_lan_tillvaxtverket.py"

  py_temp <- tempfile(fileext = ".py")
  py_resp <- GET(py_url)
  stop_for_status(py_resp)
  writeBin(httr::content(py_resp, "raw"), py_temp)

  system2("python", c(py_temp, "--outdir", tmpdir))
  sokvag_filnamn <- list.files(tmpdir, full.names = TRUE)

  retur_df <- read_xlsx(sokvag_filnamn, skip = 3) %>%            # läs in fil
    rename(region = Kategori) %>%
    filter(!is.na(region))

    antal_kol <- names(retur_df)[str_detect(tolower(names(retur_df)), "antal")]

    retur_df <- retur_df %>%
      mutate(Beskrivning = "Antal utländska gästnätter") %>%
      rename(Antal = !!sym(antal_kol))

  regionnyckel <- hamtaregtab() %>%
    filter(nchar(regionkod) == 2) %>%
    rename(Regionkod = regionkod) %>%
    mutate(region = region %>% skapa_kortnamn_lan())

  retur_df <- retur_df %>%
    left_join(regionnyckel, by = "region") %>%
    relocate(c(Regionkod, region), .after = "År") %>%
    relocate(Beskrivning, .before = Antal) %>%
    rename(regionkod = Regionkod)

  unlink(tmpdir, recursive = TRUE, force = TRUE)
  return(retur_df)
}
