from dataclasses import dataclass, fields
from typing import Optional


@dataclass
class Product:
    id: Optional[int] = None
    internal_id: str = ""
    name: str = ""
    space_id: str = "dom-betty"
    space_name: str = "Dom Betty"
    room: str = "spálňa / izba"
    main_category: str = "nabytok"
    item_type: str = "posteľ"
    store: str = ""
    country: str = "Slovensko"
    frame_price: Optional[float] = None
    original_price: Optional[float] = None
    sale_price: Optional[float] = None
    currency: str = "EUR"
    mattress_width: Optional[int] = 90
    mattress_length: Optional[int] = 200
    total_dimensions: str = "Neoverené"
    color: str = "Neoverené"
    material: str = "Neoverené"
    slats_included: Optional[bool] = None
    mattress_included: Optional[bool] = False
    product_url: str = ""
    image_url: str = ""
    additional_images: str = "[]"
    local_image: str = ""
    last_checked: str = ""
    availability: str = "Neoverené"
    notes: str = ""
    approval_status: str = "unreviewed"
    style_match_score: int = 0
    source: str = ""
    verification_data: str = "{}"
    created_at: str = ""
    updated_at: str = ""

    @classmethod
    def from_row(cls, row):
        allowed = {f.name for f in fields(cls)}
        data = {key: row[key] for key in row.keys() if key in allowed}
        for key in ("slats_included", "mattress_included"):
            if data.get(key) is not None:
                data[key] = bool(data[key])
        return cls(**data)

    def to_dict(self):
        return {f.name: getattr(self, f.name) for f in fields(self)}
