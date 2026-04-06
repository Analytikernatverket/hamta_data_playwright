
hamta_ek_bistand_individer_socialstyrelsen <- function() {

  if (!require("pacman")) install.packages("pacman")
  p_load(tidyverse,
         glue,
         httr,
         readxl)

  # skapa temporär mapp
  tmpdir <- tempfile()
  dir.create(tmpdir)

  # hämta Python-skript från Github och spara i en tillfällig mapp för att kunna anropa från system2()
  py_url <- "https://raw.githubusercontent.com/Analytikernatverket/hamta_data_playwright/main/hamta_ek_bistand_individer_socialstyrelsen.py"
  py_temp <- tempfile(fileext = ".py")
  py_resp <- GET(py_url)
  stop_for_status(py_resp)
  writeBin(httr::content(py_resp, "raw"), py_temp)

  system2("python", c(py_temp, tmpdir))
  sokvag_filnamn <- list.files(tmpdir, full.names = TRUE)

  retur_df <- map(sokvag_filnamn, ~ {

    inlasfil <- suppressMessages(read_xlsx(.x, col_names = FALSE))

    beskrivning_txt <- inlasfil[[1,1]]
    bakgrund_txt <- str_extract(beskrivning_txt, "Inrikes född|Utrikes född")
    alder_txt <- str_extract(beskrivning_txt, "(?<=Ålder: ).*$") %>% paste0(., " år")
    enhet_txt <- beskrivning_txt %>%
      str_remove("^[^,]*,") %>%
      str_remove(",.*$") %>%
      str_trim()
    kol_namn <- inlasfil[2,] %>% as.character()

    inlasfil <- inlasfil %>%
      slice(3:nrow(.)) %>%
      setNames(kol_namn)

    dataset_slutrad <- which(is.na(inlasfil[["År"]]))[1] - 1

    suppress_specific_warning(
    inlasfil <- inlasfil %>%
      slice(1:dataset_slutrad) %>%
      pivot_longer(cols = c("Januari":"December"), names_to = "Månad", values_to = "Antal") %>%
      mutate(Antal = na_if(str_replace_all(Antal, "--", NA_character_), NA_character_),
             Antal = Antal %>% as.numeric(),
             Enhet = enhet_txt,
             Bakgrund = bakgrund_txt,
             Ålder = alder_txt) %>%
      relocate(Antal, .after = last_col())
    )

    sista_kol <- names(inlasfil)[ncol(inlasfil)]

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

    # filtrera bort år-månader där samtliga värden är NA (kommande månader)
    inlasfil <- inlasfil %>%
      group_by(År, Månad) %>%
      filter(!all(across(all_of(sista_kol), is.na))) %>%
      ungroup()
  }) %>% list_rbind() # slut map-loop

  unlink(tmpdir, recursive = TRUE, force = TRUE)
  return(retur_df)
}
