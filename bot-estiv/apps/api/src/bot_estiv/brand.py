"""Tokens y reglas de marca Gardens Wood.

Estas constantes son la fuente de verdad que consultan TODOS los agentes
(ContentDesigner, Copywriter, BrandGuardian, etc.). Reflejan el manual de
identidad oficial.
"""
from __future__ import annotations

import json
import os
from dataclasses import dataclass, field
from pathlib import Path


@dataclass(frozen=True)
class BrandPalette:
    # Principales
    gris_carbon: str = "#36454F"
    blanco_hueso: str = "#F5F5DC"
    marron_quebracho: str = "#654321"
    # Acentos
    verde_eucalipto: str = "#5F8575"
    naranja_fuego: str = "#E59500"
    # Derivados de uso frecuente en overlays
    gris_suave: str = "#4E5A66"  # carbon claro para subtítulos sobre fondo blanco

    def all(self) -> list[str]:
        return [
            self.gris_carbon,
            self.blanco_hueso,
            self.marron_quebracho,
            self.verde_eucalipto,
            self.naranja_fuego,
        ]


@dataclass(frozen=True)
class BrandTypography:
    heading: str = "Playfair Display"
    body: str = "Montserrat"


@dataclass(frozen=True)
class BrandVoice:
    essence: str = (
        "Experta, serena y elegante. Evoca durabilidad, diseño atemporal y "
        "conexión natural. Inspira a construir refugios personales."
    )
    tagline: str = "Gardens Wood: Diseñado para Durar. Creado para Unir."
    pillars: dict[str, str] = field(
        default_factory=lambda: {
            "durabilidad": "Invertí una vez. Disfrutá para siempre.",
            "diseno": "Belleza que no pasa de moda.",
            "experiencia": "El escenario para tus mejores momentos.",
        }
    )
    do_use: tuple[str, ...] = (
        "Diseñado para perdurar generaciones.",
        "La nobleza del Quebracho en su máxima expresión.",
        "Creamos el espacio de encuentro que soñaste.",
        "Artesanía que se siente en cada detalle.",
    )
    dont_use: tuple[str, ...] = (
        "¡Súper resistente, no se rompe nunca!",
        "La mejor madera del mercado, ¡aprovecha!",
        "¡Oferta increíble en muebles de jardín!",
        "Producto de alta calidad a buen precio.",
    )
    forbidden_tokens: tuple[str, ...] = (
        "¡oferta",
        "el mejor",
        "la mejor",
        "súper ",
        "super ",
        "increíble",
        "aprovecha",
        "barato",
        "barata",
        "imperdible",
        "¡no te lo pierdas",
    )


@dataclass(frozen=True)
class BrandAudience:
    description: str = (
        "Hombres y mujeres de 35 a 65 años, propietarios con jardines/patios/galerías. "
        "Profesionales, empresarios y familias con poder adquisitivo medio-alto. "
        "Valoran calidad, diseño, exclusividad y legado familiar."
    )


@dataclass(frozen=True)
class BrandHashtags:
    marca: tuple[str, ...] = (
        "#GardensWood",
        "#DisenadoParaDurar",
        "#QuebrachoArgentino",
    )
    rubro: tuple[str, ...] = (
        "#Paisajismo",
        "#DisenoExterior",
        "#MueblesDeJardin",
        "#Pergolas",
        "#Decks",
        "#Fogoneros",
        "#MaderasNobles",
    )
    local: tuple[str, ...] = (
        "#Argentina",
        "#Jardineria",
        "#JardinesDeAutor",
    )


PALETTE = BrandPalette()
TYPOGRAPHY = BrandTypography()
VOICE = BrandVoice()
AUDIENCE = BrandAudience()
HASHTAGS = BrandHashtags()


# ==========  Catálogo de productos (fuente de verdad externa) ==========


def _catalog_path() -> Path:
    env_path = os.getenv("BRAND_CATALOG_PATH")
    candidates = [Path(env_path)] if env_path else []
    here = Path(__file__).resolve()
    candidates.append(Path("/app/packages/brand/catalog.json"))
    candidates.extend(parent / "packages" / "brand" / "catalog.json" for parent in here.parents)

    for candidate in candidates:
        if candidate.exists():
            return candidate

    return candidates[0] if candidates else Path("packages/brand/catalog.json")


_CATALOG_PATH = _catalog_path()


@dataclass(frozen=True)
class BrandCatalog:
    products: tuple[str, ...]
    materials: tuple[str, ...]
    services: tuple[str, ...]
    forbidden_in_prompts: tuple[str, ...]
    region: dict

    def products_str(self) -> str:
        return ", ".join(self.products)

    def forbidden_str(self) -> str:
        return ", ".join(self.forbidden_in_prompts)


def _load_catalog() -> BrandCatalog:
    if not _CATALOG_PATH.exists():
        return BrandCatalog(
            products=("pérgolas", "decks", "mesas de jardín", "bancos", "fogoneros", "cercos"),
            materials=("quebracho colorado",),
            services=("diseño a medida", "instalación"),
            forbidden_in_prompts=(),
            region={},
        )
    data = json.loads(_CATALOG_PATH.read_text(encoding="utf-8"))
    return BrandCatalog(
        products=tuple(data.get("products", [])),
        materials=tuple(data.get("materials", [])),
        services=tuple(data.get("services", [])),
        forbidden_in_prompts=tuple(data.get("forbidden_in_prompts", [])),
        region=data.get("region", {}),
    )


CATALOG = _load_catalog()


FORMATS: dict[str, tuple[int, int]] = {
    "ig_feed_square": (1080, 1080),
    "ig_feed_portrait": (1080, 1350),
    "ig_story": (1080, 1920),
    "ig_reel": (1080, 1920),
    "fb_feed": (1200, 630),
    "carousel_square": (1080, 1080),
    "carousel_portrait": (1080, 1350),
}


BRAND_SUMMARY = """\
# Marca Gardens Wood — Referencia rápida
- Esencia: {essence}
- Tagline: {tagline}
- Arquetipo: El Creador
- Paleta principal: {main_palette}
- Paleta acentos: {accent_palette}
- Tipografías: títulos {heading}, cuerpo {body}
- Tono: experto, sereno, elegante, inspirador, cercano
- Evitar: superlativos, jerga agresiva, ofertas tipo "¡aprovecha!"
""".format(
    essence=VOICE.essence,
    tagline=VOICE.tagline,
    main_palette=f"{PALETTE.gris_carbon}, {PALETTE.blanco_hueso}, {PALETTE.marron_quebracho}",
    accent_palette=f"{PALETTE.verde_eucalipto}, {PALETTE.naranja_fuego}",
    heading=TYPOGRAPHY.heading,
    body=TYPOGRAPHY.body,
)
