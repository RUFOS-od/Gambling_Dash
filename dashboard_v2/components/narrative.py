"""Petits helpers pour rédiger les encarts d'analyse à partir des données.

Les encarts doivent refléter le sens réel des évolutions (hausse, baisse,
stabilité) plutôt qu'un texte figé, sinon ils deviennent faux dès qu'un KPI
se retourne d'une vague à l'autre.
"""

from data.loader import sort_vagues, vague_short


def to_num(delta):
    """'+6.7' / '-5.0' / '0' / None -> float ou None."""
    if delta is None:
        return None
    try:
        return float(str(delta).replace(",", ".").replace("+", "").strip())
    except ValueError:
        return None


def trend_word(delta, threshold=0.5) -> str:
    """Verbe d'évolution : 'progresse', 'recule', 'est stable'."""
    d = to_num(delta)
    if d is None:
        return "s'établit"  # pas de vague de comparaison sélectionnée
    if abs(d) < threshold:
        return "reste stable"
    return "progresse" if d > 0 else "recule"


def signed(delta, unit="pt") -> str:
    """'+6.7 pt' / '-5.0 pt' / 'stable'."""
    d = to_num(delta)
    if d is None:
        return "sans vague de comparaison"
    if d == 0:
        return f"0 {unit}"
    return f"{d:+.1f} {unit}"


def prev_wave_label(vague_dict: dict) -> str:
    """Libellé court de l'avant-dernière vague disponible (ex. 'V3')."""
    keys = sort_vagues([k for k, v in vague_dict.items() if v is not None])
    return vague_short(keys[-2]) if len(keys) >= 2 else ""


def latest_wave_label(vague_dict: dict) -> str:
    keys = sort_vagues([k for k, v in vague_dict.items() if v is not None])
    return vague_short(keys[-1]) if keys else ""


def leader_of(scores: dict, exclude=None):
    """(marque, valeur) en tête d'un dict {marque: valeur}, hors `exclude`."""
    items = [(b, v) for b, v in scores.items() if b != exclude and v is not None]
    if not items:
        return None, None
    return max(items, key=lambda x: x[1])
