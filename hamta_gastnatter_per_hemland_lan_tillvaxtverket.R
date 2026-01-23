
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

  retur_df <- map(sokvag_filnamn, ~ {

    lansnamn <- .x %>%
      str_extract("(?<=/)[^/]+$") %>%  # allt efter sista "/"
      str_extract("^[^_]+")

    suppressMessages(inlasfil <- read_xlsx(.x, skip = 3) %>%                  # läs in fil
      mutate(Region = lansnamn) %>%
        filter(!is.na(Land))
      )

    enhet_kol <- inlasfil[[1,1]]
    bakgrund_varde <- str_extract(enhet_kol, "[^,]*$") %>% str_trim()
    antal_kol <- names(inlasfil)[str_detect(tolower(names(inlasfil)), "antal")]

    inlasfil <- inlasfil %>%
      mutate(Beskrivning = antal_kol) %>%
      rename(Antal = !!sym(antal_kol))

  }) %>% list_rbind()

  regionnyckel <- hamtaregtab() %>%
    filter(nchar(regionkod) == 2) %>%
    rename(Regionkod = regionkod) %>%
    mutate(region = region %>% skapa_kortnamn_lan())

  retur_df <- retur_df %>%
    left_join(regionnyckel, by = c("Region" = "region")) %>%
    relocate(c(Regionkod, Region), .after = "År") %>%
    relocate(Beskrivning, .after = Land)

  unlink(tmpdir, recursive = TRUE, force = TRUE)
  return(retur_df)
}
