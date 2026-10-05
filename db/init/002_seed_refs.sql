INSERT INTO ref_type_ruche (libelle, is_system) VALUES
('Production', TRUE),
('Essaim', TRUE),
('Starter', TRUE),
('Finisseur', TRUE),
('Banque a males', TRUE),
('Nuclei', TRUE),
('Elevage', TRUE),
('Ruche tronc', TRUE),
('Ruche pedagogique', TRUE),
('Piege a essaim', TRUE)
ON CONFLICT DO NOTHING;

INSERT INTO ref_statut_ruche (libelle, is_system) VALUES
('Active', TRUE),
('Morte', TRUE),
('Bourdonneuse', TRUE),
('Hivernee', TRUE),
('Essaimee', TRUE),
('Orpheline', TRUE),
('Pillee', TRUE),
('Suspecte maladie', TRUE),
('En quarantaine', TRUE)
ON CONFLICT DO NOTHING;

INSERT INTO ref_action_visite (libelle, is_system) VALUES
('Controle', TRUE),
('Recolte', TRUE),
('Pose de hausse', TRUE),
('Retrait de hausse', TRUE),
('Cassage cellules', TRUE),
('Prelevement cadre essaim', TRUE),
('Nourrissement', TRUE),
('Visite sanitaire', TRUE),
('Hivernage', TRUE),
('Clipsage reine', TRUE),
('Marquage reine', TRUE),
('Nettoyage plancher', TRUE),
('Pose chasse abeilles', TRUE)
ON CONFLICT DO NOTHING;

INSERT INTO ref_type_intervention (libelle, is_system) VALUES
('Traitement varroa', TRUE),
('Nourrissement', TRUE),
('Suspicion maladie', TRUE),
('Traitement nosemose', TRUE),
('Traitement fausse teigne', TRUE),
('Destruction sanitaire', TRUE)
ON CONFLICT DO NOTHING;

INSERT INTO ref_action_cadre (libelle, is_system) VALUES
('Ajout cadre cire gaufree', TRUE),
('Ajout cadre construit sec', TRUE),
('Ajout cadre nourriture', TRUE),
('Ajout cadre a males', TRUE),
('Retrait vieux cadre', TRUE),
('Retrait cadre couvain', TRUE),
('Rotation corps hausse', TRUE)
ON CONFLICT DO NOTHING;

INSERT INTO ref_type_materiel (libelle, is_system) VALUES
('Corps', TRUE),
('Hausse', TRUE),
('Nourrisseur', TRUE),
('Plancher', TRUE),
('Couvre-cadre', TRUE),
('Ruchette', TRUE),
('Toit', TRUE),
('Partition', TRUE),
('Cadre', TRUE),
('Grille a reine', TRUE)
ON CONFLICT DO NOTHING;
