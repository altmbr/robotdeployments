# Taxonomy v1 (2026-11-05): two MECE dimensions, multi-tag allowed

Each company gets one or more **use cases** (what the robot does) and one or more **verticals** (who buys it).
Within a dimension the categories don't overlap and together cover everything. Pick EVERY tag that
applies to a material share of the company's deployments, and mark ONE `primary` in each dimension
(the largest share of units). Use slugs exactly. If nothing fits, use `other` and say why in notes.

## Use case: what the robot does
| slug | covers | examples |
|---|---|---|
| `move_goods_indoor` | moving items inside a facility: AMR/AGV transport, goods-to-person, tugging, restaurant/hotel/hospital delivery robots | Locus, Geek+, Pudu BellaBot, Aethon TUG |
| `storage_retrieval` | automated storage & retrieval systems (cube/shuttle AS/RS) | AutoStore, Exotec, Hai, Symbotic |
| `pick_sort` | grasping individual items: each-picking, sorting, induction, kitting, recycling sorting | Covariant, RightHand, AMP, Ambi sort |
| `load_unload_palletize` | trucks/containers/pallets: unloading, loading, (de)palletizing, case handling | Pickle, Dexterity, Boston Dynamics Stretch |
| `manufacturing_process` | welding, assembly, machine tending, painting, material removal, packaging on a line | Fanuc, UR, Tutor (line work), Bright Machines |
| `inspection_security` | patrol, inspection, monitoring, mapping, surveying, ISR (non-strike) | Knightscope, ANYbotics, Gecko, Skydio Dock |
| `cleaning` | commercial floor cleaning, window/solar/hull cleaning, sanitation | Brain Corp, Gausium, Avidbots |
| `food_prep` | cooking, drinks, food assembly | Miso, Chef Robotics, Hyphen |
| `interaction_guidance` | reception, guidance, telepresence, companionship, education, entertainment | SoftBank Pepper, OrionStar, Paro |
| `delivery_outdoor` | last-mile sidewalk/road/air delivery of goods | Starship, Serve, Zipline, Wing, Neolix |
| `passenger_transport` | robotaxis, autonomous shuttles/buses | Waymo, Apollo Go, Pony.ai |
| `freight_haul` | autonomous trucking, yard/terminal tractors, mining haulage | Aurora, Kodiak, Outrider, EACON |
| `crop_application` | spraying, spreading, seeding/planting | DJI Agriculture, XAG, Guardian |
| `crop_care_harvest` | weeding, thinning, pruning, harvesting, field tractors/autonomy kits | Carbon Robotics, Bonsai, Monarch, Burro |
| `livestock` | milking, feeding, barn cleaning, herd tasks | Lely, DeLaval, GEA |
| `construction_tasks` | layout, drilling, bricklaying, rebar, demolition, earthmoving autonomy | Dusty, Built Robotics, Hilti Jaibot |
| `surgery_clinical` | surgical robots, clinical procedures, pharmacy dispensing | Intuitive, Stryker Mako, Omnicell |
| `assist_rehab` | exoskeletons, rehab, eldercare/patient assistance | Ekso, Cyberdyne, Diligent Moxi* |
| `lab_automation` | liquid handling, lab workcells, cloud labs | Opentrons, Multiply Labs, Medra |
| `defense_strike` | combat, strike, loitering munitions, EOD, armed UGVs | Neros, AeroVironment Switchblade, Anduril |
| `household_chores` | home vacuum/mop, lawn, pool, window | iRobot, Roborock, Ecovacs |
| `general_purpose` | multi-task platforms sold for many jobs (most humanoids, mobile manipulators w/o a dominant task) | Figure, Unitree H1/G1, AgiBot |

*Moxi is hospital delivery → `move_goods_indoor` primary; tag `assist_rehab` only if a material share is patient-facing assistance.

## Vertical: who buys it
| slug | buyers |
|---|---|
| `logistics_warehousing` | 3PLs, e-commerce fulfillment, parcel carriers, distribution centers |
| `retail_grocery` | stores, grocery, store-attached micro-fulfillment |
| `manufacturing` | factories of all kinds (auto, electronics, metal, CPG production lines) |
| `food_processing` | meat, produce packing, beverage and food plants |
| `agriculture_crops` | farms, orchards, vineyards, greenhouses |
| `agriculture_livestock` | dairy, poultry, swine, aquaculture |
| `healthcare` | hospitals, clinics, pharmacies, eldercare facilities |
| `life_sciences` | pharma, biotech, research labs |
| `hospitality_food_service` | restaurants, hotels, casinos, catering, canteens |
| `facilities_real_estate` | offices, airports, malls, campuses, property managers, schools (as facilities) |
| `mobility_transit` | riders, ride-hail, public transit operators |
| `freight_trucking` | shippers and carriers moving freight between facilities |
| `construction` | builders, contractors, infrastructure |
| `energy_mining_utilities` | mining, oil & gas, power, solar, utilities, industrial inspection |
| `defense_public_safety` | militaries, governments, police, fire, border |
| `consumer` | households and individuals |
| `education_research` | universities, labs buying robots as research platforms, schools (as teaching tools) |

## Funding fields
`stage` uses: `pre_seed`, `seed`, `series_a`, `series_b`, `series_c`, `series_d_plus`, `growth` (late private, incl. strategic), `debt`, `grant`, `ipo`, `public` (listed: no rounds), `acquired`, `corporate_division` (unit of a larger company: no rounds), `unknown`.
Every round needs `date` (YYYY-MM or YYYY-MM-DD), `amount_usd` (number or null), `lead_investors` (list), `investors` (list of EVERY participant incl. leads, as named in the source), `source_url`, and a verbatim `quote` (<=300 chars). No source, no round.
