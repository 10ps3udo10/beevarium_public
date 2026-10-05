-- Le format rend deux stocks non interchangeables: un corps de ruchette ne peut
-- pas accueillir une ruche de production. Il est porte a la fois par la ruche et
-- par le materiel, afin de calculer les capacites format par format.
ALTER TABLE ruches ADD COLUMN IF NOT EXISTS format_ruche VARCHAR(30);
ALTER TABLE materiel_atelier ADD COLUMN IF NOT EXISTS format_materiel VARCHAR(30);

CREATE INDEX IF NOT EXISTS idx_ruches_format ON ruches(user_id, format_ruche);
CREATE INDEX IF NOT EXISTS idx_materiel_format ON materiel_atelier(user_id, format_materiel);
