from deep_translator import GoogleTranslator
import scrapy

class HlProjet2Spider(scrapy.Spider):
    name = "hl_projet2"
    allowed_domains = ["openlibrary.org"]

    subjects = [
        "science_fiction", "romance", "history", "fantasy", "biography",
        "art", "children", "mystery", "drama", "education",
        "travel", "music", "technology", "poetry", "health"
    ] # tableau de catégorie pour ne pas avoir 2500 science-fiction
    start_urls = [f"https://openlibrary.org/subjects/{s}.json?limit=100&offset=0" for s in subjects]

    compteur = 0
    max_items = 20
    current_subject_index = 0  # index pour tourner entre les catégories
    livres_par_page = 100 # propre au site, changer si un nouveau site

    translator = GoogleTranslator(source="en", target="fr")
    cache_traductions = {}  # cache local pour accélérer

    # pour suivre la position (offset et index) par catégorie
    progression = {s: {"offset": 0, "index": 0, "works": []} for s in subjects}

    def start_requests(self):
        # commence avec la première catégorie
        yield from self.request_next_category()

    def request_next_category(self):
        # demande la page actuelle de la catégorie
        sujet = self.subjects[self.current_subject_index]
        info = self.progression[sujet]

        # si la liste actuelle est vide, on va chercher une nouvelle page
        if not info["works"]:
            url = f"https://openlibrary.org/subjects/{sujet}.json?limit={self.livres_par_page}&offset={info['offset']}"
            yield scrapy.Request(url, callback=self.parse, meta={"categorie": sujet})
        else:
            # sinon, on prend le prochain livre
            work = info["works"].pop(0)
            yield from self.parse_book(work, sujet)
            yield from self.next_cycle()

    def next_cycle(self):
        # boucle sur les catégories
        self.current_subject_index = (self.current_subject_index + 1) % len(self.subjects)

        if self.compteur < self.max_items:
            yield from self.request_next_category()
        else:
            # quand on a atteint le nombre d'items souhaités, on sort du spider
            self.logger.info(f"Récolte de données complétée ({self.max_items} livres).")
            raise scrapy.exceptions.CloseSpider(reason="max_items_reached")

    # tarduction avec cache et gestion d'erreur
    def translate_text(self, texte):
        if not texte:
            return ""
        texte = texte.strip()
        if texte in self.cache_traductions:
            return self.cache_traductions[texte]
        try:
            traduction = self.translator.translate(texte)
            self.cache_traductions[texte] = traduction
            return traduction
        except Exception as e:
            # retour du texte original si problème
            self.logger.warning(f"Erreur de traduction pour '{texte}': {e}")
            return texte

    # récupère un seul livre par catégorie et passe à la suivante
    def parse(self, response):
        categorie = response.meta["categorie"]
        data = response.json()
        works = data.get("works", [])

        if not works:
            self.logger.warning(f"Aucun livre trouvé pour {categorie}")
            yield from self.next_cycle()
            return
        
        # stock les livres dans la progression
        info = self.progression[categorie]
        info["works"] = works
        info["offset"] += self.livres_par_page

        # prend le premier livre et continue
        work = info["works"].pop(0)
        yield from self.parse_book(work, categorie)
        yield from self.next_cycle()


    def parse_book(self, work, categorie):
        # quand on a atteint le nombre d'items souhaités, on sort du spider
        if self.compteur >= self.max_items:
            self.logger.info(f"Récolte de données complétée ({self.max_items} items).")
            raise scrapy.exceptions.CloseSpider(reason="max_items_reached")

        self.compteur += 1

        # données texte
        titre = work.get("title", "")
        auteur = work["authors"][0]["name"] if work.get("authors") else ""
        couverture = f"https://covers.openlibrary.org/b/id/{work['cover_id']}-L.jpg" if work.get("cover_id") else ""
        sujets = work.get("subject", [])

        if sujets:
            # prends le premier élément et le découpe sur les virgules pour faire un tableau
            sous_categorie = [s.strip() for s in sujets[0].split(",")]
        else:
            sous_categorie = ["Général"]

        # données numériques
        nombre_editions = int(work.get("edition_count", 0))
        note_popularite = round(nombre_editions / 10, 2)  

        # traduction des données texte
        titre = self.translate_text(titre)
        auteur = self.translate_text(auteur)
        categorie = self.translate_text(categorie.replace("_", " ").title())
        sous_categorie = [self.translate_text(s) for s in sous_categorie] # traduction de tout le tableau

        yield {
            "id_livre": self.compteur-1,
            "titre": titre, # français avec des accents
            "auteur": auteur,
            "categorie": categorie, # trier ou regrouper
            "sous_categorie": sous_categorie, # trier ou regrouper
            "nombre_editions": nombre_editions,  # entier
            "note_popularite": note_popularite,  # décimal
            "image_url": couverture, # url pointant vers l'image
        }
