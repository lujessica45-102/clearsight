-- California USDA offices (NRCS service centers, FSA, Forest Service, ARS) for fire-weather and general demos.
-- Same schema as parser/facilities.sql; lat/lon are NULL and filled by backend/connect.py's geocoder.
-- Every address and phone is copied from the cited public page (accessed 2026-10-11).
INSERT OR IGNORE INTO public_facilities (
    name, agency, address, phone, counties_served,
    latitude, longitude, permanent_status, operating_status,
    source_name, source_url, source_date
) VALUES
(
    'Redding Service Center', 'USDA NRCS',
    '3644 Avtech Pkwy, Redding, CA 96002',
    '530-691-5836', 'Shasta',
    NULL, NULL, 'open', 'open',
    'California Land CAN: NRCS Local Offices Serving California (Redding Service Center)',
    'https://www.californialandcan.org/local-resources/Redding-Service-Center/59564',
    '2026-10-11'
),
(
    'Shasta County FSA', 'USDA FSA',
    '3644 Avtech Pkwy, Redding, CA 96002',
    '530-691-5836', 'Shasta',
    NULL, NULL, 'open', 'open',
    'California Land CAN: Shasta County Farm Service Agency',
    'https://www.californialandcan.org/local-resources/Shasta-County-Farm-Service-Agency/59563',
    '2026-10-11'
),
(
    'Oroville Service Center', 'USDA NRCS',
    '150 Chuck Yeager Way, Oroville, CA 95965',
    '530-534-0112', 'Butte',
    NULL, NULL, 'open', 'open',
    'California Land CAN: NRCS Local Offices Serving California (Oroville Service Center)',
    'https://www.californialandcan.org/local-resources/Oroville-Service-Center/63734',
    '2026-10-11'
),
(
    'Butte County FSA', 'USDA FSA',
    '150 Chuck Yeager Way, Oroville, CA 95965',
    '530-534-0112', 'Butte',
    NULL, NULL, 'open', 'open',
    'California Land CAN: Butte County Farm Service Agency',
    'https://www.californialandcan.org/local-resources/Butte-County-Farm-Service-Agency/59513',
    '2026-10-11'
),
(
    'Susanville Service Center', 'USDA NRCS',
    '170 Russell Ave, Suite C, Susanville, CA 96130',
    '530-257-4127', 'Lassen',
    NULL, NULL, 'open', 'open',
    'California Land CAN: NRCS Local Offices Serving California (Susanville Service Center)',
    'https://www.californialandcan.org/local-resources/Susanville-Service-Center/59532',
    '2026-10-11'
),
(
    'Petaluma Service Center', 'USDA NRCS',
    '5401 Old Redwood Highway, Suite 100, Petaluma, CA 94954',
    '707-794-1242', 'Sonoma',
    NULL, NULL, 'open', 'open',
    'California Land CAN: NRCS Local Offices Serving California (Petaluma Service Center)',
    'https://www.californialandcan.org/local-resources/Petaluma-Service-Center/59570',
    '2026-10-11'
),
(
    'Napa Service Center', 'USDA NRCS',
    '1303 Jefferson St, Suite 500B, Napa, CA 94559',
    '707-690-3111', 'Napa',
    NULL, NULL, 'open', 'open',
    'California Land CAN: NRCS Local Offices Serving California (Napa Service Center)',
    'https://www.californialandcan.org/local-resources/Napa-Service-Center/59545',
    '2026-10-11'
),
(
    'Elk Grove Service Center', 'USDA NRCS',
    '9701 Dino Dr, Suite 190, Elk Grove, CA 95624',
    '916-582-6637', 'Sacramento',
    NULL, NULL, 'open', 'open',
    'California Land CAN: NRCS Local Offices Serving California (Elk Grove Service Center)',
    'https://www.californialandcan.org/local-resources/Elk-Grove-Service-Center/59552',
    '2026-10-11'
),
(
    'Fresno Service Center', 'USDA NRCS',
    '4625 W Jennifer Ave, Suite 109, Fresno, CA 93722',
    '559-276-7494', 'Fresno',
    NULL, NULL, 'open', 'open',
    'California Land CAN: NRCS Local Offices Serving California (Fresno Service Center)',
    'https://www.californialandcan.org/local-resources/Fresno-Service-Center/59520',
    '2026-10-11'
),
(
    'Bakersfield Service Center', 'USDA NRCS',
    '5080 California Avenue, Suite 150, Bakersfield, CA 93309',
    '661-281-2764', 'Kern',
    NULL, NULL, 'open', 'open',
    'California Land CAN: NRCS Local Offices Serving California (Bakersfield Service Center)',
    'https://www.californialandcan.org/local-resources/Bakersfield-Service-Center/59528',
    '2026-10-11'
),
(
    'Oxnard Field Office', 'USDA NRCS',
    '3550 S Harbor Blvd, Suite 2-202, Oxnard, CA 93035',
    '805-984-2358', 'Ventura',
    NULL, NULL, 'open', 'open',
    'California Land CAN: NRCS Local Offices Serving California (Oxnard Field Office)',
    'https://www.californialandcan.org/local-resources/Oxnard-Field-Office/59577',
    '2026-10-11'
),
(
    'Lancaster Service Center', 'USDA NRCS',
    '44811 Date Ave, Lancaster, CA 93534',
    '661-945-2604', 'Los Angeles',
    NULL, NULL, 'open', 'open',
    'California Land CAN: NRCS Local Offices Serving California (Lancaster Service Center)',
    'https://www.californialandcan.org/local-resources/Lancaster-Service-Center/59534',
    '2026-10-11'
),
(
    'Redlands Local Partnership Office', 'USDA NRCS',
    '25864 Business Center Dr, Suite K, Redlands, CA 92374',
    '909-799-7407', 'San Bernardino',
    NULL, NULL, 'open', 'open',
    'California Land CAN: NRCS Local Offices Serving California (Redlands Local Partnership Office)',
    'https://www.californialandcan.org/local-resources/Redlands-Local-Partnership-Office/59556',
    '2026-10-11'
),
(
    'Escondido Service Center', 'USDA NRCS',
    '900 Canterbury Pl, Suite 320, Escondido, CA 92025',
    '760-745-2061', 'San Diego',
    NULL, NULL, 'open', 'open',
    'California Land CAN: NRCS Local Offices Serving California (Escondido Service Center)',
    'https://www.californialandcan.org/local-resources/Escondido-Service-Center/59557',
    '2026-10-11'
),
(
    'Angeles National Forest Supervisor''s Office', 'USDA FS',
    '701 N. Santa Anita Ave, Arcadia, CA 91006',
    '(626) 574-1613', 'Angeles National Forest',
    NULL, NULL, 'open', 'open',
    'Forest Service: Angeles National Forest Offices',
    'https://www.fs.usda.gov/r05/angeles/offices',
    '2026-10-11'
),
(
    'San Bernardino National Forest Supervisor''s Office', 'USDA FS',
    '602 S. Tippecanoe Ave, San Bernardino, CA 92408',
    '(909) 382-2600', 'San Bernardino National Forest',
    NULL, NULL, 'open', 'open',
    'Forest Service: San Bernardino National Forest Offices',
    'https://www.fs.usda.gov/r05/sanbernardino/offices',
    '2026-10-11'
),
(
    'Los Padres National Forest Headquarters', 'USDA FS',
    '1980 Old Mission Drive, Solvang, CA 93463',
    '805-968-6640', 'Los Padres National Forest',
    NULL, NULL, 'open', 'open',
    'Forest Service: Los Padres National Forest Offices',
    'https://www.fs.usda.gov/r05/lospadres/offices',
    '2026-10-11'
),
(
    'Cleveland National Forest Supervisor''s Office', 'USDA FS',
    '10845 Rancho Bernardo Road, Suite 200, San Diego, CA 92127',
    '(858) 673-6180', 'Cleveland National Forest',
    NULL, NULL, 'open', 'open',
    'Forest Service: Cleveland National Forest Offices',
    'https://www.fs.usda.gov/r05/cleveland/offices',
    '2026-10-11'
),
(
    'Plumas National Forest Supervisor''s Office', 'USDA FS',
    '159 Lawrence St., Quincy, CA 95971',
    '530-283-2050', 'Plumas National Forest',
    NULL, NULL, 'open', 'open',
    'Forest Service: Plumas National Forest Offices',
    'https://www.fs.usda.gov/r05/plumas/offices',
    '2026-10-11'
),
(
    'Lassen National Forest Supervisor''s Office', 'USDA FS',
    '2550 Riverside Drive, Susanville, CA 96130',
    '(530) 257-2151', 'Lassen National Forest',
    NULL, NULL, 'open', 'open',
    'Forest Service: Lassen National Forest Offices',
    'https://www.fs.usda.gov/r05/lassen/offices',
    '2026-10-11'
),
(
    'Shasta-Trinity National Forest Supervisor''s Office', 'USDA FS',
    '3644 Avtech Parkway, Redding, CA 96002',
    '530-226-2500', 'Shasta-Trinity National Forest',
    NULL, NULL, 'open', 'open',
    'Forest Service: Shasta-Trinity National Forest Offices',
    'https://www.fs.usda.gov/r05/shasta-trinity/offices',
    '2026-10-11'
),
(
    'Tahoe National Forest Headquarters', 'USDA FS',
    '631 Coyote St., Nevada City, CA 95959',
    '530-265-4531', 'Tahoe National Forest',
    NULL, NULL, 'open', 'open',
    'Forest Service: Tahoe National Forest Offices',
    'https://www.fs.usda.gov/r05/tahoe/offices',
    '2026-10-11'
),
(
    'Western Regional Research Center (ARS Albany)', 'USDA ARS',
    '800 Buchanan Street, Albany, CA 94710',
    '510-559-5600', 'Alameda',
    NULL, NULL, 'open', 'open',
    'USDA ARS: Western Regional Research Center, Albany, CA',
    'https://www.ars.usda.gov/pacific-west-area/albany-ca/wrrc/',
    '2026-10-11'
),
(
    'San Joaquin Valley Agricultural Sciences Center (ARS Parlier)', 'USDA ARS',
    '9611 S. Riverbend Avenue, Parlier, CA 93648',
    '559-596-2702', 'Fresno',
    NULL, NULL, 'open', 'open',
    'USDA ARS: San Joaquin Valley Agricultural Sciences Center, Parlier, CA',
    'https://www.ars.usda.gov/pacific-west-area/parlier/sjvasc/',
    '2026-10-11'
),
(
    'Salinity Laboratory (ARS Riverside)', 'USDA ARS',
    '450 West Big Springs Road, Riverside, CA 92507',
    '951 369-4815', 'Riverside',
    NULL, NULL, 'open', 'open',
    'USDA ARS: Agricultural Water Efficiency and Salinity Research Unit, Riverside, CA',
    'https://www.ars.usda.gov/pacific-west-area/riverside-ca/agricultural-water-efficiency-and-salinity-research-unit/',
    '2026-10-11'
),
(
    'Crop Improvement and Protection Research (ARS Salinas)', 'USDA ARS',
    '1636 E. Alisal St., Salinas, CA 93905',
    '(831)755-2864', 'Monterey',
    NULL, NULL, 'open', 'open',
    'USDA ARS: Crop Improvement and Protection Research, Salinas, CA',
    'https://www.ars.usda.gov/pacific-west-area/salinas-ca/crop-improvement-and-protection-research/',
    '2026-10-11'
),
(
    'Visalia Service Center', 'USDA NRCS',
    '3530 W Orchard Ct, Visalia, CA 93277',
    '559-734-8732', 'Tulare',
    NULL, NULL, 'open', 'open',
    'California Land CAN: NRCS Local Offices Serving California (Visalia Service Center)',
    'https://www.californialandcan.org/local-resources/Visalia-Service-Center/63540',
    '2026-10-11'
),
(
    'Sierra National Forest Supervisor''s Office', 'USDA FS',
    '1600 Tollhouse Road, Clovis, CA 93611',
    '(559) 297-0706', 'Sierra National Forest',
    NULL, NULL, 'open', 'open',
    'Forest Service: Sierra National Forest Offices',
    'https://www.fs.usda.gov/r05/sierra/offices',
    '2026-10-11'
),
(
    'Mendocino National Forest Supervisor''s Office', 'USDA FS',
    '825 North Humboldt Avenue, Willows, CA 95988',
    '(530) 934-3316', 'Mendocino National Forest',
    NULL, NULL, 'open', 'open',
    'Forest Service: Mendocino National Forest Offices',
    'https://www.fs.usda.gov/r05/mendocino/offices',
    '2026-10-11'
);
