# -*- coding: utf-8 -*-

# Copyright 2016-2020 Mike Fährmann
#
# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License version 2 as
# published by the Free Software Foundation.

"""Extractors for FoOlSlide based sites"""

from .common import (
    Extractor,
    ChapterExtractor,
    MangaExtractor,
    SharedConfigMixin,
    Message,
    generate_extractors,
)
from .. import text, util
import base64
import json
import re


class FoolslideBase(SharedConfigMixin):
    """Base class for FoOlSlide extractors"""
    basecategory = "foolslide"

    def request(self, url):
        return Extractor.request(
            self, url, encoding="utf-8", method="POST", data={"adult": "true"})

    @staticmethod
    def parse_chapter_url(url, data):
        info = url.partition("/read/")[2].rstrip("/").split("/")
        lang = info[1].partition("-")[0]
        data["lang"] = lang
        data["language"] = util.code_to_language(lang)
        data["volume"] = text.parse_int(info[2])
        data["chapter"] = text.parse_int(info[3])
        data["chapter_minor"] = "." + info[4] if len(info) >= 5 else ""
        data["title"] = data["chapter_string"].partition(":")[2].strip()
        return data


class FoolslideChapterExtractor(FoolslideBase, ChapterExtractor):
    """Base class for chapter extractors for FoOlSlide based sites"""
    directory_fmt = ("{category}", "{manga}", "{chapter_string}")
    archive_fmt = "{id}"
    pattern_fmt = r"(/read/[^/?&#]+/[a-z-]+/\d+/\d+(?:/\d+)?)"
    decode = "default"

    def items(self):
        page = self.request(self.gallery_url).text
        data = self.metadata(page)
        imgs = self.images(page)

        data["count"] = len(imgs)
        data["chapter_id"] = text.parse_int(imgs[0]["chapter_id"])

        yield Message.Version, 1
        yield Message.Directory, data
        for data["page"], image in enumerate(imgs, 1):
            try:
                url = image["url"]
                del image["url"]
                del image["chapter_id"]
                del image["thumb_url"]
            except KeyError:
                pass
            for key in ("height", "id", "size", "width"):
                image[key] = text.parse_int(image[key])
            data.update(image)
            text.nameext_from_url(data["filename"], data)
            yield Message.Url, url, data

    def metadata(self, page):
        extr = text.extract_from(page)
        extr('<h1 class="tbtitle dnone">', '')
        return self.parse_chapter_url(self.gallery_url, {
            "manga"         : text.unescape(extr('title="', '"')).strip(),
            "chapter_string": text.unescape(extr('title="', '"')),
        })

    def images(self, page):
        data = None

        if self.decode == "base64":
            pos = page.find("'fromCharCode'")
            if pos >= 0:
                blob = text.extract(page, "'", "'", pos+15)[0]
                base64_data = re.sub(r"[a-zA-Z]", _decode_jaiminisbox, blob)
            else:
                base64_data = text.extract(page, 'atob("', '"')[0]
            if base64_data:
                data = base64.b64decode(base64_data.encode()).decode()
        elif self.decode == "double":
            pos = page.find("[{")
            if pos >= 0:
                data = text.extract(page, " = ", ";", pos)[0]

        if not data:
            data = text.extract(page, "var pages = ", ";")[0]
        return json.loads(data)


class FoolslideMangaExtractor(FoolslideBase, MangaExtractor):
    """Base class for manga extractors for FoOlSlide based sites"""
    pattern_fmt = r"(/series/[^/?&#]+)"

    def chapters(self, page):
        extr = text.extract_from(page)
        manga = text.unescape(extr('<h1 class="title">', '</h1>')).strip()
        author = extr('<b>Author</b>: ', '<br')
        artist = extr('<b>Artist</b>: ', '<br')

        results = []
        while True:
            url = extr('<div class="title"><a href="', '"')
            if not url:
                return results
            results.append((url, self.parse_chapter_url(url, {
                "manga": manga, "author": author, "artist": artist,
                "chapter_string": extr('title="', '"'),
                "group"         : extr('title="', '"'),
            })))


def _decode_jaiminisbox(match):
    c = match.group(0)

    # ord("Z") == 90, ord("z") == 122
    N = 90 if c <= "Z" else 122
    C = ord(c) + 13

    return chr(C if N >= C else (C - 26))


EXTRACTORS = {
    "dokireader": {
        "root": "https://kobato.hologfx.com/reader",
        "test-chapter":
            (("https://kobato.hologfx.com/reader/read/"
              "hitoribocchi_no_oo_seikatsu/en/3/34"), {
                "keyword": "6e719ac86f0c6dab89390dd7e507e678459e0dbc",
            }),
        "test-manga":
            (("https://kobato.hologfx.com/reader/series/"
              "boku_ha_ohimesama_ni_narenai/"), {
                "url": "1c1f5a7258ce4f631f5fc32be548d78a6a57990d",
                "keyword": "614d89a6045b85c822cbd3e67578ea7577dfc995",
            }),
    },
    "jaiminisbox": {
        "root": "https://jaiminisbox.com/reader",
        "pattern": r"(?:www\.)?jaiminisbox\.com/reader",
        "extra": {"decode": "base64"},
        "test-chapter":
            ("https://jaiminisbox.com/reader/read/oshi-no-ko/en/0/1/", {
                "keyword": "d6435cfc1522293a42517a4aadda95a8631da0b3",
            }),
        "test-manga":
            ("https://jaiminisbox.com/reader/series/oshi-no-ko/", {
                "count": ">= 10",
            }),
    },
    "kireicake": {
        "root": "https://reader.kireicake.com",
        "test-chapter":
            ("https://reader.kireicake.com/read/wonderland/en/1/1/", {
                "url": "b2d36bc0bc67e4c461c3a4d6444a2fd339f5d07e",
                "keyword": "9f80947920a325e33aea7f5cd69ea669171903b6",
            }),
        "test-manga":
            ("https://reader.kireicake.com/series/wonderland/", {
                "url": "d067b649af1cc88fa8c8b698fde04a10909fd169",
                "keyword": "268f43772fb239888ca5c5f6a4f65f99ffb3eefb",
            }),
    },
    "powermanga": {
        "root": "https://read.powermanga.org",
        "pattern": r"read(?:er)?\.powermanga\.org",
        "test-chapter":
            (("https://read.powermanga.org"
              "/read/one_piece_digital_colour_comics/en/0/75/"), {
                "url": "854c5817f8f767e1bccd05fa9d58ffb5a4b09384",
                "keyword": "a60c42f2634b7387899299d411ff494ed0ad6dbe",
            }),
        "test-manga":
            (("https://read.powermanga.org"
              "/series/one_piece_digital_colour_comics/"), {
                "count": ">= 1",
                "keyword": {
                    "chapter": int,
                    "chapter_minor": str,
                    "chapter_string": str,
                    "group": "PowerManga",
                    "lang": "en",
                    "language": "English",
                    "manga": "One Piece Digital Colour Comics",
                    "title": str,
                    "volume": int,
                },
            }),
    },
    "sensescans": {
        "root": "https://sensescans.com/reader",
        "pattern": r"(?:(?:www\.)?sensescans\.com/reader"
                   r"|reader\.sensescans\.com)",
        "test-chapter": (
            (("https://sensescans.com/reader/read/"
              "magi__labyrinth_of_magic/en/37/369/"), {
                  "url": "8bbc59a995640bbb944c0b1be06a490909b58be1",
                  "keyword": "07acd84fb18a9f1fd6dff5befe711bcca0ff9988",
            }),
            (("https://reader.sensescans.com/read/"
              "magi__labyrinth_of_magic/en/37/369/"), {
                  "url": "8bbc59a995640bbb944c0b1be06a490909b58be1",
                  "keyword": "07acd84fb18a9f1fd6dff5befe711bcca0ff9988",
            }),
        ),
        "test-manga":
            ("https://sensescans.com/reader/series/yotsubato/", {
                "url": "ee4dca7c421bf15ac039200f8c0bcb0858153640",
                "keyword": "f94961bd731bd878bbd4d48555bc3ace1d937364",
            }),
    },
    "worldthree": {
        "root": "http://www.slide.world-three.org",
        "pattern": r"(?:www\.)?slide\.world-three\.org",
        "test-chapter": (
            (("http://www.slide.world-three.org"
              "/read/black_bullet/en/2/7/page/1"), {
                "url": "be2f04f6e2d311b35188094cfd3e768583271584",
                "keyword": "967d536a65de4d52478d5b666a1760b181eddb6e",
            }),
            (("http://www.slide.world-three.org"
              "/read/idolmster_cg_shuffle/en/0/4/2/"), {
                "url": "6028ea5ca282744f925dfad92eeb98509f9cc78c",
                "keyword": "f3cfe2ad3388991f1d045c85d0fa94795a7694dc",
            }),
        ),
        "test-manga":
            ("http://www.slide.world-three.org/series/black_bullet/", {
                "url": "5743b93512d26e6b540d90a7a5d69208b6d4a738",
                "keyword": "3a24f1088b4d7f3b798a96163f21ca251293a120",
            }),
    },
    "_ckey": "chapterclass",
}

generate_extractors(EXTRACTORS, globals(), (
    FoolslideChapterExtractor,
    FoolslideMangaExtractor,
))
