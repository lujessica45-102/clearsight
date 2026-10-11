// GENERATED from the team's data — do not edit by hand.
//   facilities: parser/facilities.sql (25 Florida USDA offices, all fields)
//   emergencies: closure/replay/michael_2018.json, snapshot 2 (archived real NWS warnings)
//   lat/lon: town-level approximations; the backend geocodes exact addresses
export const SCENARIO = {
 "id": "michael_2018",
 "title": "Hurricane Michael - Florida Panhandle, October 9-11, 2018",
 "asOf": "2018-10-10T09:00:00Z",
 "label": "Wed Oct 10, 4:00 AM CDT - the 4 AM closure decision; ~8h before landfall",
 "disclaimer": "HISTORICAL REPLAY. Every alert, text and observation here is an archived real National Weather Service / IEM record from October 2018, selected by time filter and replayed. It is NOT live data and must never be presented as a current alert. Road closures are not included (no archived 511 data was available).",
 "facts": {
  "storm": "Hurricane Michael (AL142018), 7-11 October 2018",
  "landfall_utc": "2018-10-10T17:30Z (approx.; 12:30 PM CDT, Wednesday)",
  "landfall_location": "Near Tyndall Air Force Base / Mexico Beach, Florida (SE of Panama City)",
  "landfall_intensity": "Category 5, estimated 140 kt (~160 mph) maximum sustained winds; 919 mb central pressure",
  "impacts": "16 direct US deaths, about $25 billion damage (NHC TCR)",
  "storm_surge": "6-9 ft AGL near Tyndall AFB, 4-6 ft around Panama City/St. Andrew Bay (NHC TCR)",
  "source_urls": [
   "https://www.nhc.noaa.gov/data/tcr/AL142018_Michael.pdf"
  ]
 }
};

export const FLORIDA_FACILITIES = [
 {
  "id": "florida-nrcs-state-office",
  "name": "Florida NRCS State Office",
  "short": "Florida NRCS State Office",
  "lat": 29.684,
  "lon": -82.395,
  "address": "4500 NW 27th Avenue, Building A, Gainesville, FL 32606",
  "agency": "USDA NRCS",
  "phone": "(352) 338-9500",
  "countiesServed": "Florida statewide",
  "permanentStatus": "open",
  "operatingStatus": "open",
  "source": {
   "name": "Florida NRCS/FSA Service Center Contact List",
   "url": "https://www.nrcs.usda.gov/sites/default/files/2024-08/Florida-NRCS-FSA-Service-Center-Contact-List-FINAL-FINAL_Aug2024.pdf",
   "date": "2024-06-21"
  },
  "total": null,
  "affected": null,
  "opinion": null,
  "reasoning": null,
  "email": null,
  "status": "normal",
  "alert": null,
  "alertPolygon": null,
  "alerts": [],
  "bullets": [
   "No Hurricane Michael warnings covered this office",
   "USDA NRCS \u00b7 serves Florida statewide",
   "Phone: (352) 338-9500"
  ]
 },
 {
  "id": "gainesville-service-center",
  "name": "Gainesville Service Center",
  "short": "Gainesville",
  "lat": 29.707,
  "lon": -82.338,
  "address": "5709 NW 13th Street, Gainesville, FL 32653",
  "agency": "USDA NRCS",
  "phone": "(352) 376-7414",
  "countiesServed": "Alachua; Bradford",
  "permanentStatus": "open",
  "operatingStatus": "open",
  "source": {
   "name": "Florida NRCS/FSA Service Center Contact List",
   "url": "https://www.nrcs.usda.gov/sites/default/files/2024-08/Florida-NRCS-FSA-Service-Center-Contact-List-FINAL-FINAL_Aug2024.pdf",
   "date": "2024-06-21"
  },
  "total": null,
  "affected": null,
  "opinion": null,
  "reasoning": null,
  "email": null,
  "status": "normal",
  "alert": null,
  "alertPolygon": null,
  "alerts": [],
  "bullets": [
   "No Hurricane Michael warnings covered this office",
   "USDA NRCS \u00b7 serves Alachua; Bradford",
   "Phone: (352) 376-7414"
  ]
 },
 {
  "id": "alachua-county-fsa",
  "name": "Alachua County FSA",
  "short": "Alachua FSA",
  "lat": 29.707,
  "lon": -82.338,
  "address": "5709 NW 13th Street, Gainesville, FL 32653",
  "agency": "USDA FSA",
  "phone": "(352) 376-7414",
  "countiesServed": "Alachua",
  "permanentStatus": "open",
  "operatingStatus": "open",
  "source": {
   "name": "Florida NRCS/FSA Service Center Contact List",
   "url": "https://www.nrcs.usda.gov/sites/default/files/2024-08/Florida-NRCS-FSA-Service-Center-Contact-List-FINAL-FINAL_Aug2024.pdf",
   "date": "2024-06-21"
  },
  "total": null,
  "affected": null,
  "opinion": null,
  "reasoning": null,
  "email": null,
  "status": "normal",
  "alert": null,
  "alertPolygon": null,
  "alerts": [],
  "bullets": [
   "No Hurricane Michael warnings covered this office",
   "USDA FSA \u00b7 serves Alachua",
   "Phone: (352) 376-7414"
  ]
 },
 {
  "id": "baldwin-service-center",
  "name": "Baldwin Service Center",
  "short": "Baldwin",
  "lat": 30.302,
  "lon": -81.975,
  "address": "260 US Highway 301 N, Baldwin, FL 32234",
  "agency": "USDA NRCS",
  "phone": "(904) 266-0088",
  "countiesServed": "Baker; Duval; Nassau",
  "permanentStatus": "open",
  "operatingStatus": "open",
  "source": {
   "name": "Florida NRCS/FSA Service Center Contact List",
   "url": "https://www.nrcs.usda.gov/sites/default/files/2024-08/Florida-NRCS-FSA-Service-Center-Contact-List-FINAL-FINAL_Aug2024.pdf",
   "date": "2024-06-21"
  },
  "total": null,
  "affected": null,
  "opinion": null,
  "reasoning": null,
  "email": null,
  "status": "normal",
  "alert": null,
  "alertPolygon": null,
  "alerts": [],
  "bullets": [
   "No Hurricane Michael warnings covered this office",
   "USDA NRCS \u00b7 serves Baker; Duval; Nassau",
   "Phone: (904) 266-0088"
  ]
 },
 {
  "id": "duval-county-fsa",
  "name": "Duval County FSA",
  "short": "Duval FSA",
  "lat": 30.302,
  "lon": -81.975,
  "address": "260 US Highway 301 N, Baldwin, FL 32234",
  "agency": "USDA FSA",
  "phone": "(904) 266-0088 ext. 2",
  "countiesServed": "Duval",
  "permanentStatus": "open",
  "operatingStatus": "open",
  "source": {
   "name": "Florida NRCS/FSA Service Center Contact List",
   "url": "https://www.nrcs.usda.gov/sites/default/files/2024-08/Florida-NRCS-FSA-Service-Center-Contact-List-FINAL-FINAL_Aug2024.pdf",
   "date": "2024-06-21"
  },
  "total": null,
  "affected": null,
  "opinion": null,
  "reasoning": null,
  "email": null,
  "status": "normal",
  "alert": null,
  "alertPolygon": null,
  "alerts": [],
  "bullets": [
   "No Hurricane Michael warnings covered this office",
   "USDA FSA \u00b7 serves Duval",
   "Phone: (904) 266-0088 ext. 2"
  ]
 },
 {
  "id": "bonifay-service-center",
  "name": "Bonifay Service Center",
  "short": "Bonifay",
  "lat": 30.791,
  "lon": -85.68,
  "address": "103 N Oklahoma Street, Bonifay, FL 32425-2311",
  "agency": "USDA NRCS",
  "phone": "(850) 547-2850",
  "countiesServed": "Bay; Holmes; Washington",
  "permanentStatus": "open",
  "operatingStatus": "open",
  "source": {
   "name": "Florida NRCS/FSA Service Center Contact List",
   "url": "https://www.nrcs.usda.gov/sites/default/files/2024-08/Florida-NRCS-FSA-Service-Center-Contact-List-FINAL-FINAL_Aug2024.pdf",
   "date": "2024-06-21"
  },
  "total": null,
  "affected": null,
  "opinion": null,
  "reasoning": null,
  "email": null,
  "status": "unknown",
  "alert": {
   "type": "hurricane",
   "title": "Hurricane Warning",
   "area": "Covers this office (Bay; Holmes; Washington)",
   "expires": "end time not in NWS archive",
   "source": "NWS Tallahassee FL"
  },
  "alertPolygon": [
   [
    -85.68,
    30.11
   ],
   [
    -85.67,
    30.14
   ],
   [
    -85.62,
    30.09
   ],
   [
    -85.56,
    30.09
   ],
   [
    -85.53,
    30.06
   ],
   [
    -85.5,
    30.03
   ],
   [
    -85.42,
    30.04
   ],
   [
    -85.43,
    30.05
   ],
   [
    -85.45,
    30.03
   ],
   [
    -85.51,
    30.09
   ],
   [
    -85.53,
    30.12
   ],
   [
    -85.57,
    30.12
   ],
   [
    -85.64,
    30.14
   ],
   [
    -85.71,
    30.17
   ],
   [
    -85.72,
    30.2
   ],
   [
    -85.69,
    30.22
   ],
   [
    -85.62,
    30.26
   ],
   [
    -85.59,
    30.29
   ],
   [
    -85.58,
    30.33
   ],
   [
    -85.63,
    30.28
   ],
   [
    -85.67,
    30.27
   ],
   [
    -85.72,
    30.24
   ],
   [
    -85.75,
    30.29
   ],
   [
    -85.8,
    30.29
   ],
   [
    -85.85,
    30.28
   ],
   [
    -85.85,
    30.23
   ],
   [
    -85.79,
    30.25
   ],
   [
    -85.76,
    30.24
   ],
   [
    -85.76,
    30.21
   ],
   [
    -85.75,
    30.2
   ],
   [
    -85.74,
    30.16
   ],
   [
    -85.73,
    30.14
   ],
   [
    -85.78,
    30.16
   ],
   [
    -85.84,
    30.2
   ],
   [
    -85.9,
    30.22
   ],
   [
    -85.95,
    30.25
   ],
   [
    -86.04,
    30.28
   ],
   [
    -86.13,
    30.32
   ],
   [
    -86.23,
    30.34
   ],
   [
    -86.32,
    30.37
   ],
   [
    -86.38,
    30.39
   ],
   [
    -86.3,
    30.41
   ],
   [
    -86.24,
    30.4
   ],
   [
    -86.26,
    30.42
   ],
   [
    -86.22,
    30.41
   ],
   [
    -86.17,
    30.39
   ],
   [
    -86.12,
    30.43
   ],
   [
    -86.14,
    30.46
   ],
   [
    -86.19,
    30.46
   ],
   [
    -86.22,
    30.48
   ],
   [
    -86.25,
    30.49
   ],
   [
    -86.3,
    30.47
   ],
   [
    -86.39,
    30.99
   ],
   [
    -86.12,
    31.18
   ],
   [
    -85.7,
    31.21
   ],
   [
    -85.67,
    31.27
   ],
   [
    -85.59,
    31.27
   ],
   [
    -85.49,
    31.29
   ],
   [
    -85.08,
    31.32
   ],
   [
    -85.08,
    31.43
   ],
   [
    -85.05,
    31.5
   ],
   [
    -84.97,
    31.5
   ],
   [
    -84.81,
    31.49
   ],
   [
    -84.79,
    31.44
   ],
   [
    -84.53,
    31.44
   ],
   [
    -84.51,
    31.43
   ],
   [
    -84.44,
    31.45
   ],
   [
    -83.76,
    31.32
   ],
   [
    -83.52,
    31.3
   ],
   [
    -83.53,
    31.19
   ],
   [
    -83.55,
    31.14
   ],
   [
    -83.58,
    31.08
   ],
   [
    -83.55,
    31.06
   ],
   [
    -83.47,
    31.01
   ],
   [
    -83.43,
    30.96
   ],
   [
    -83.43,
    30.89
   ],
   [
    -83.36,
    30.88
   ],
   [
    -83.38,
    30.83
   ],
   [
    -83.44,
    30.81
   ],
   [
    -83.46,
    30.76
   ],
   [
    -83.46,
    30.71
   ],
   [
    -83.42,
    30.69
   ],
   [
    -83.4,
    30.68
   ],
   [
    -83.5,
    30.65
   ],
   [
    -83.61,
    30.58
   ],
   [
    -83.67,
    30.55
   ],
   [
    -83.73,
    30.51
   ],
   [
    -83.72,
    30.47
   ],
   [
    -83.73,
    30.42
   ],
   [
    -83.79,
    30.39
   ],
   [
    -83.8,
    30.35
   ],
   [
    -83.82,
    30.3
   ],
   [
    -83.9,
    30.25
   ],
   [
    -83.93,
    30.19
   ],
   [
    -83.51,
    29.85
   ],
   [
    -82.99,
    29.47
   ],
   [
    -83.02,
    29.43
   ],
   [
    -83.03,
    29.39
   ],
   [
    -83.06,
    29.36
   ],
   [
    -83.08,
    29.34
   ],
   [
    -83.11,
    29.33
   ],
   [
    -83.17,
    29.3
   ],
   [
    -83.17,
    29.34
   ],
   [
    -83.18,
    29.37
   ],
   [
    -83.2,
    29.4
   ],
   [
    -83.26,
    29.43
   ],
   [
    -83.29,
    29.44
   ],
   [
    -83.31,
    29.47
   ],
   [
    -83.35,
    29.49
   ],
   [
    -83.39,
    29.52
   ],
   [
    -83.41,
    29.59
   ],
   [
    -83.41,
    29.63
   ],
   [
    -83.4,
    29.66
   ],
   [
    -83.47,
    29.69
   ],
   [
    -83.51,
    29.71
   ],
   [
    -83.55,
    29.75
   ],
   [
    -83.57,
    29.78
   ],
   [
    -83.6,
    29.83
   ],
   [
    -83.63,
    29.88
   ],
   [
    -83.66,
    29.9
   ],
   [
    -83.69,
    29.93
   ],
   [
    -83.73,
    29.94
   ],
   [
    -83.75,
    29.97
   ],
   [
    -83.78,
    29.98
   ],
   [
    -83.84,
    29.99
   ],
   [
    -83.88,
    30.02
   ],
   [
    -83.95,
    30.05
   ],
   [
    -83.98,
    30.09
   ],
   [
    -84.0,
    30.11
   ],
   [
    -84.03,
    30.11
   ],
   [
    -84.07,
    30.1
   ],
   [
    -84.12,
    30.08
   ],
   [
    -84.16,
    30.07
   ],
   [
    -84.21,
    30.1
   ],
   [
    -84.26,
    30.11
   ],
   [
    -84.3,
    30.06
   ],
   [
    -84.33,
    30.08
   ],
   [
    -84.36,
    30.06
   ],
   [
    -84.38,
    30.04
   ],
   [
    -84.39,
    30.01
   ],
   [
    -84.37,
    30.01
   ],
   [
    -84.37,
    29.97
   ],
   [
    -84.43,
    30.0
   ],
   [
    -84.44,
    29.98
   ],
   [
    -84.34,
    29.94
   ],
   [
    -84.38,
    29.91
   ],
   [
    -84.47,
    29.92
   ],
   [
    -84.52,
    29.92
   ],
   [
    -84.56,
    29.89
   ],
   [
    -84.62,
    29.87
   ],
   [
    -84.66,
    29.84
   ],
   [
    -84.75,
    29.8
   ],
   [
    -84.81,
    29.76
   ],
   [
    -84.92,
    29.73
   ],
   [
    -84.88,
    29.77
   ],
   [
    -84.86,
    29.8
   ],
   [
    -84.91,
    29.79
   ],
   [
    -84.94,
    29.75
   ],
   [
    -84.99,
    29.71
   ],
   [
    -85.16,
    29.71
   ],
   [
    -85.26,
    29.69
   ],
   [
    -85.31,
    29.77
   ],
   [
    -85.32,
    29.83
   ],
   [
    -85.34,
    29.87
   ],
   [
    -85.4,
    29.93
   ],
   [
    -85.48,
    29.98
   ],
   [
    -85.52,
    30.0
   ],
   [
    -85.56,
    30.03
   ],
   [
    -85.59,
    30.06
   ],
   [
    -85.62,
    30.06
   ],
   [
    -85.65,
    30.1
   ]
  ],
  "alerts": [
   {
    "event": "Hurricane Warning",
    "sender": "NWS Tallahassee FL",
    "issued": "2018-10-08T21:42Z"
   },
   {
    "event": "Flash Flood Watch",
    "sender": "NWS Tallahassee FL",
    "issued": "2018-10-10T00:00Z"
   }
  ],
  "bullets": [
   "In effect here: Hurricane Warning, Flash Flood Watch",
   "USDA NRCS \u00b7 serves Bay; Holmes; Washington",
   "Phone: (850) 547-2850"
  ]
 },
 {
  "id": "holmes-county-fsa",
  "name": "Holmes County FSA",
  "short": "Holmes FSA",
  "lat": 30.791,
  "lon": -85.68,
  "address": "103 N Oklahoma Street, Bonifay, FL 32425-2311",
  "agency": "USDA FSA",
  "phone": "(850) 547-2850 ext. 2",
  "countiesServed": "Holmes",
  "permanentStatus": "open",
  "operatingStatus": "open",
  "source": {
   "name": "Florida NRCS/FSA Service Center Contact List",
   "url": "https://www.nrcs.usda.gov/sites/default/files/2024-08/Florida-NRCS-FSA-Service-Center-Contact-List-FINAL-FINAL_Aug2024.pdf",
   "date": "2024-06-21"
  },
  "total": null,
  "affected": null,
  "opinion": null,
  "reasoning": null,
  "email": null,
  "status": "unknown",
  "alert": {
   "type": "hurricane",
   "title": "Hurricane Warning",
   "area": "Covers this office (Holmes)",
   "expires": "end time not in NWS archive",
   "source": "NWS Tallahassee FL"
  },
  "alertPolygon": [
   [
    -85.68,
    30.11
   ],
   [
    -85.67,
    30.14
   ],
   [
    -85.62,
    30.09
   ],
   [
    -85.56,
    30.09
   ],
   [
    -85.53,
    30.06
   ],
   [
    -85.5,
    30.03
   ],
   [
    -85.42,
    30.04
   ],
   [
    -85.43,
    30.05
   ],
   [
    -85.45,
    30.03
   ],
   [
    -85.51,
    30.09
   ],
   [
    -85.53,
    30.12
   ],
   [
    -85.57,
    30.12
   ],
   [
    -85.64,
    30.14
   ],
   [
    -85.71,
    30.17
   ],
   [
    -85.72,
    30.2
   ],
   [
    -85.69,
    30.22
   ],
   [
    -85.62,
    30.26
   ],
   [
    -85.59,
    30.29
   ],
   [
    -85.58,
    30.33
   ],
   [
    -85.63,
    30.28
   ],
   [
    -85.67,
    30.27
   ],
   [
    -85.72,
    30.24
   ],
   [
    -85.75,
    30.29
   ],
   [
    -85.8,
    30.29
   ],
   [
    -85.85,
    30.28
   ],
   [
    -85.85,
    30.23
   ],
   [
    -85.79,
    30.25
   ],
   [
    -85.76,
    30.24
   ],
   [
    -85.76,
    30.21
   ],
   [
    -85.75,
    30.2
   ],
   [
    -85.74,
    30.16
   ],
   [
    -85.73,
    30.14
   ],
   [
    -85.78,
    30.16
   ],
   [
    -85.84,
    30.2
   ],
   [
    -85.9,
    30.22
   ],
   [
    -85.95,
    30.25
   ],
   [
    -86.04,
    30.28
   ],
   [
    -86.13,
    30.32
   ],
   [
    -86.23,
    30.34
   ],
   [
    -86.32,
    30.37
   ],
   [
    -86.38,
    30.39
   ],
   [
    -86.3,
    30.41
   ],
   [
    -86.24,
    30.4
   ],
   [
    -86.26,
    30.42
   ],
   [
    -86.22,
    30.41
   ],
   [
    -86.17,
    30.39
   ],
   [
    -86.12,
    30.43
   ],
   [
    -86.14,
    30.46
   ],
   [
    -86.19,
    30.46
   ],
   [
    -86.22,
    30.48
   ],
   [
    -86.25,
    30.49
   ],
   [
    -86.3,
    30.47
   ],
   [
    -86.39,
    30.99
   ],
   [
    -86.12,
    31.18
   ],
   [
    -85.7,
    31.21
   ],
   [
    -85.67,
    31.27
   ],
   [
    -85.59,
    31.27
   ],
   [
    -85.49,
    31.29
   ],
   [
    -85.08,
    31.32
   ],
   [
    -85.08,
    31.43
   ],
   [
    -85.05,
    31.5
   ],
   [
    -84.97,
    31.5
   ],
   [
    -84.81,
    31.49
   ],
   [
    -84.79,
    31.44
   ],
   [
    -84.53,
    31.44
   ],
   [
    -84.51,
    31.43
   ],
   [
    -84.44,
    31.45
   ],
   [
    -83.76,
    31.32
   ],
   [
    -83.52,
    31.3
   ],
   [
    -83.53,
    31.19
   ],
   [
    -83.55,
    31.14
   ],
   [
    -83.58,
    31.08
   ],
   [
    -83.55,
    31.06
   ],
   [
    -83.47,
    31.01
   ],
   [
    -83.43,
    30.96
   ],
   [
    -83.43,
    30.89
   ],
   [
    -83.36,
    30.88
   ],
   [
    -83.38,
    30.83
   ],
   [
    -83.44,
    30.81
   ],
   [
    -83.46,
    30.76
   ],
   [
    -83.46,
    30.71
   ],
   [
    -83.42,
    30.69
   ],
   [
    -83.4,
    30.68
   ],
   [
    -83.5,
    30.65
   ],
   [
    -83.61,
    30.58
   ],
   [
    -83.67,
    30.55
   ],
   [
    -83.73,
    30.51
   ],
   [
    -83.72,
    30.47
   ],
   [
    -83.73,
    30.42
   ],
   [
    -83.79,
    30.39
   ],
   [
    -83.8,
    30.35
   ],
   [
    -83.82,
    30.3
   ],
   [
    -83.9,
    30.25
   ],
   [
    -83.93,
    30.19
   ],
   [
    -83.51,
    29.85
   ],
   [
    -82.99,
    29.47
   ],
   [
    -83.02,
    29.43
   ],
   [
    -83.03,
    29.39
   ],
   [
    -83.06,
    29.36
   ],
   [
    -83.08,
    29.34
   ],
   [
    -83.11,
    29.33
   ],
   [
    -83.17,
    29.3
   ],
   [
    -83.17,
    29.34
   ],
   [
    -83.18,
    29.37
   ],
   [
    -83.2,
    29.4
   ],
   [
    -83.26,
    29.43
   ],
   [
    -83.29,
    29.44
   ],
   [
    -83.31,
    29.47
   ],
   [
    -83.35,
    29.49
   ],
   [
    -83.39,
    29.52
   ],
   [
    -83.41,
    29.59
   ],
   [
    -83.41,
    29.63
   ],
   [
    -83.4,
    29.66
   ],
   [
    -83.47,
    29.69
   ],
   [
    -83.51,
    29.71
   ],
   [
    -83.55,
    29.75
   ],
   [
    -83.57,
    29.78
   ],
   [
    -83.6,
    29.83
   ],
   [
    -83.63,
    29.88
   ],
   [
    -83.66,
    29.9
   ],
   [
    -83.69,
    29.93
   ],
   [
    -83.73,
    29.94
   ],
   [
    -83.75,
    29.97
   ],
   [
    -83.78,
    29.98
   ],
   [
    -83.84,
    29.99
   ],
   [
    -83.88,
    30.02
   ],
   [
    -83.95,
    30.05
   ],
   [
    -83.98,
    30.09
   ],
   [
    -84.0,
    30.11
   ],
   [
    -84.03,
    30.11
   ],
   [
    -84.07,
    30.1
   ],
   [
    -84.12,
    30.08
   ],
   [
    -84.16,
    30.07
   ],
   [
    -84.21,
    30.1
   ],
   [
    -84.26,
    30.11
   ],
   [
    -84.3,
    30.06
   ],
   [
    -84.33,
    30.08
   ],
   [
    -84.36,
    30.06
   ],
   [
    -84.38,
    30.04
   ],
   [
    -84.39,
    30.01
   ],
   [
    -84.37,
    30.01
   ],
   [
    -84.37,
    29.97
   ],
   [
    -84.43,
    30.0
   ],
   [
    -84.44,
    29.98
   ],
   [
    -84.34,
    29.94
   ],
   [
    -84.38,
    29.91
   ],
   [
    -84.47,
    29.92
   ],
   [
    -84.52,
    29.92
   ],
   [
    -84.56,
    29.89
   ],
   [
    -84.62,
    29.87
   ],
   [
    -84.66,
    29.84
   ],
   [
    -84.75,
    29.8
   ],
   [
    -84.81,
    29.76
   ],
   [
    -84.92,
    29.73
   ],
   [
    -84.88,
    29.77
   ],
   [
    -84.86,
    29.8
   ],
   [
    -84.91,
    29.79
   ],
   [
    -84.94,
    29.75
   ],
   [
    -84.99,
    29.71
   ],
   [
    -85.16,
    29.71
   ],
   [
    -85.26,
    29.69
   ],
   [
    -85.31,
    29.77
   ],
   [
    -85.32,
    29.83
   ],
   [
    -85.34,
    29.87
   ],
   [
    -85.4,
    29.93
   ],
   [
    -85.48,
    29.98
   ],
   [
    -85.52,
    30.0
   ],
   [
    -85.56,
    30.03
   ],
   [
    -85.59,
    30.06
   ],
   [
    -85.62,
    30.06
   ],
   [
    -85.65,
    30.1
   ]
  ],
  "alerts": [
   {
    "event": "Hurricane Warning",
    "sender": "NWS Tallahassee FL",
    "issued": "2018-10-08T21:42Z"
   },
   {
    "event": "Flash Flood Watch",
    "sender": "NWS Tallahassee FL",
    "issued": "2018-10-10T00:00Z"
   }
  ],
  "bullets": [
   "In effect here: Hurricane Warning, Flash Flood Watch",
   "USDA FSA \u00b7 serves Holmes",
   "Phone: (850) 547-2850 ext. 2"
  ]
 },
 {
  "id": "cocoa-partnership-office",
  "name": "Cocoa Partnership Office",
  "short": "Cocoa Partnership Office",
  "lat": 28.386,
  "lon": -80.742,
  "address": "3695 Lake Drive, Cocoa, FL 32926-4219",
  "agency": "USDA NRCS",
  "phone": "(321) 745-6515",
  "countiesServed": "Brevard",
  "permanentStatus": "open",
  "operatingStatus": "open",
  "source": {
   "name": "Florida NRCS/FSA Service Center Contact List",
   "url": "https://www.nrcs.usda.gov/sites/default/files/2024-08/Florida-NRCS-FSA-Service-Center-Contact-List-FINAL-FINAL_Aug2024.pdf",
   "date": "2024-06-21"
  },
  "total": null,
  "affected": null,
  "opinion": null,
  "reasoning": null,
  "email": null,
  "status": "normal",
  "alert": null,
  "alertPolygon": null,
  "alerts": [],
  "bullets": [
   "No Hurricane Michael warnings covered this office",
   "USDA NRCS \u00b7 serves Brevard",
   "Phone: (321) 745-6515"
  ]
 },
 {
  "id": "osceola-brevard-county-fsa",
  "name": "Osceola-Brevard County FSA",
  "short": "Osceola-Brevard FSA",
  "lat": 28.292,
  "lon": -81.408,
  "address": "1921 Kissimmee Valley Lane, Kissimmee, FL 34744",
  "agency": "USDA FSA",
  "phone": "(407) 847-4201",
  "countiesServed": "Osceola; Brevard",
  "permanentStatus": "open",
  "operatingStatus": "open",
  "source": {
   "name": "Florida NRCS/FSA Service Center Contact List",
   "url": "https://www.nrcs.usda.gov/sites/default/files/2024-08/Florida-NRCS-FSA-Service-Center-Contact-List-FINAL-FINAL_Aug2024.pdf",
   "date": "2024-06-21"
  },
  "total": null,
  "affected": null,
  "opinion": null,
  "reasoning": null,
  "email": null,
  "status": "normal",
  "alert": null,
  "alertPolygon": null,
  "alerts": [],
  "bullets": [
   "No Hurricane Michael warnings covered this office",
   "USDA FSA \u00b7 serves Osceola; Brevard",
   "Phone: (407) 847-4201"
  ]
 },
 {
  "id": "royal-palm-beach-center",
  "name": "Royal Palm Beach Center",
  "short": "Royal Palm Beach Center",
  "lat": 26.708,
  "lon": -80.23,
  "address": "420 S State Road 7, Royal Palm Beach, FL 33414",
  "agency": "USDA NRCS",
  "phone": "(561) 792-2727",
  "countiesServed": "Broward; Palm Beach",
  "permanentStatus": "open",
  "operatingStatus": "open",
  "source": {
   "name": "Florida NRCS/FSA Service Center Contact List",
   "url": "https://www.nrcs.usda.gov/sites/default/files/2024-08/Florida-NRCS-FSA-Service-Center-Contact-List-FINAL-FINAL_Aug2024.pdf",
   "date": "2024-06-21"
  },
  "total": null,
  "affected": null,
  "opinion": null,
  "reasoning": null,
  "email": null,
  "status": "normal",
  "alert": null,
  "alertPolygon": null,
  "alerts": [],
  "bullets": [
   "No Hurricane Michael warnings covered this office",
   "USDA NRCS \u00b7 serves Broward; Palm Beach",
   "Phone: (561) 792-2727"
  ]
 },
 {
  "id": "palm-beach-county-fsa",
  "name": "Palm Beach County FSA",
  "short": "Palm Beach FSA",
  "lat": 26.708,
  "lon": -80.23,
  "address": "420 S State Road 7, Royal Palm Beach, FL 33414",
  "agency": "USDA FSA",
  "phone": "(561) 792-2727",
  "countiesServed": "Palm Beach",
  "permanentStatus": "open",
  "operatingStatus": "open",
  "source": {
   "name": "Florida NRCS/FSA Service Center Contact List",
   "url": "https://www.nrcs.usda.gov/sites/default/files/2024-08/Florida-NRCS-FSA-Service-Center-Contact-List-FINAL-FINAL_Aug2024.pdf",
   "date": "2024-06-21"
  },
  "total": null,
  "affected": null,
  "opinion": null,
  "reasoning": null,
  "email": null,
  "status": "normal",
  "alert": null,
  "alertPolygon": null,
  "alerts": [],
  "bullets": [
   "No Hurricane Michael warnings covered this office",
   "USDA FSA \u00b7 serves Palm Beach",
   "Phone: (561) 792-2727"
  ]
 },
 {
  "id": "blountstown-service-center",
  "name": "Blountstown Service Center",
  "short": "Blountstown",
  "lat": 30.443,
  "lon": -85.047,
  "address": "17413 NW Leonard Street, Blountstown, FL 32424",
  "agency": "USDA NRCS",
  "phone": "(850) 674-8271",
  "countiesServed": "Calhoun; Franklin; Gulf; Liberty",
  "permanentStatus": "open",
  "operatingStatus": "open",
  "source": {
   "name": "Florida NRCS/FSA Service Center Contact List",
   "url": "https://www.nrcs.usda.gov/sites/default/files/2024-08/Florida-NRCS-FSA-Service-Center-Contact-List-FINAL-FINAL_Aug2024.pdf",
   "date": "2024-06-21"
  },
  "total": null,
  "affected": null,
  "opinion": null,
  "reasoning": null,
  "email": null,
  "status": "unknown",
  "alert": {
   "type": "hurricane",
   "title": "Hurricane Warning",
   "area": "Covers this office (Calhoun; Franklin; Gulf; Liberty)",
   "expires": "end time not in NWS archive",
   "source": "NWS Tallahassee FL"
  },
  "alertPolygon": [
   [
    -85.68,
    30.11
   ],
   [
    -85.67,
    30.14
   ],
   [
    -85.62,
    30.09
   ],
   [
    -85.56,
    30.09
   ],
   [
    -85.53,
    30.06
   ],
   [
    -85.5,
    30.03
   ],
   [
    -85.42,
    30.04
   ],
   [
    -85.43,
    30.05
   ],
   [
    -85.45,
    30.03
   ],
   [
    -85.51,
    30.09
   ],
   [
    -85.53,
    30.12
   ],
   [
    -85.57,
    30.12
   ],
   [
    -85.64,
    30.14
   ],
   [
    -85.71,
    30.17
   ],
   [
    -85.72,
    30.2
   ],
   [
    -85.69,
    30.22
   ],
   [
    -85.62,
    30.26
   ],
   [
    -85.59,
    30.29
   ],
   [
    -85.58,
    30.33
   ],
   [
    -85.63,
    30.28
   ],
   [
    -85.67,
    30.27
   ],
   [
    -85.72,
    30.24
   ],
   [
    -85.75,
    30.29
   ],
   [
    -85.8,
    30.29
   ],
   [
    -85.85,
    30.28
   ],
   [
    -85.85,
    30.23
   ],
   [
    -85.79,
    30.25
   ],
   [
    -85.76,
    30.24
   ],
   [
    -85.76,
    30.21
   ],
   [
    -85.75,
    30.2
   ],
   [
    -85.74,
    30.16
   ],
   [
    -85.73,
    30.14
   ],
   [
    -85.78,
    30.16
   ],
   [
    -85.84,
    30.2
   ],
   [
    -85.9,
    30.22
   ],
   [
    -85.95,
    30.25
   ],
   [
    -86.04,
    30.28
   ],
   [
    -86.13,
    30.32
   ],
   [
    -86.23,
    30.34
   ],
   [
    -86.32,
    30.37
   ],
   [
    -86.38,
    30.39
   ],
   [
    -86.3,
    30.41
   ],
   [
    -86.24,
    30.4
   ],
   [
    -86.26,
    30.42
   ],
   [
    -86.22,
    30.41
   ],
   [
    -86.17,
    30.39
   ],
   [
    -86.12,
    30.43
   ],
   [
    -86.14,
    30.46
   ],
   [
    -86.19,
    30.46
   ],
   [
    -86.22,
    30.48
   ],
   [
    -86.25,
    30.49
   ],
   [
    -86.3,
    30.47
   ],
   [
    -86.39,
    30.99
   ],
   [
    -86.12,
    31.18
   ],
   [
    -85.7,
    31.21
   ],
   [
    -85.67,
    31.27
   ],
   [
    -85.59,
    31.27
   ],
   [
    -85.49,
    31.29
   ],
   [
    -85.08,
    31.32
   ],
   [
    -85.08,
    31.43
   ],
   [
    -85.05,
    31.5
   ],
   [
    -84.97,
    31.5
   ],
   [
    -84.81,
    31.49
   ],
   [
    -84.79,
    31.44
   ],
   [
    -84.53,
    31.44
   ],
   [
    -84.51,
    31.43
   ],
   [
    -84.44,
    31.45
   ],
   [
    -83.76,
    31.32
   ],
   [
    -83.52,
    31.3
   ],
   [
    -83.53,
    31.19
   ],
   [
    -83.55,
    31.14
   ],
   [
    -83.58,
    31.08
   ],
   [
    -83.55,
    31.06
   ],
   [
    -83.47,
    31.01
   ],
   [
    -83.43,
    30.96
   ],
   [
    -83.43,
    30.89
   ],
   [
    -83.36,
    30.88
   ],
   [
    -83.38,
    30.83
   ],
   [
    -83.44,
    30.81
   ],
   [
    -83.46,
    30.76
   ],
   [
    -83.46,
    30.71
   ],
   [
    -83.42,
    30.69
   ],
   [
    -83.4,
    30.68
   ],
   [
    -83.5,
    30.65
   ],
   [
    -83.61,
    30.58
   ],
   [
    -83.67,
    30.55
   ],
   [
    -83.73,
    30.51
   ],
   [
    -83.72,
    30.47
   ],
   [
    -83.73,
    30.42
   ],
   [
    -83.79,
    30.39
   ],
   [
    -83.8,
    30.35
   ],
   [
    -83.82,
    30.3
   ],
   [
    -83.9,
    30.25
   ],
   [
    -83.93,
    30.19
   ],
   [
    -83.51,
    29.85
   ],
   [
    -82.99,
    29.47
   ],
   [
    -83.02,
    29.43
   ],
   [
    -83.03,
    29.39
   ],
   [
    -83.06,
    29.36
   ],
   [
    -83.08,
    29.34
   ],
   [
    -83.11,
    29.33
   ],
   [
    -83.17,
    29.3
   ],
   [
    -83.17,
    29.34
   ],
   [
    -83.18,
    29.37
   ],
   [
    -83.2,
    29.4
   ],
   [
    -83.26,
    29.43
   ],
   [
    -83.29,
    29.44
   ],
   [
    -83.31,
    29.47
   ],
   [
    -83.35,
    29.49
   ],
   [
    -83.39,
    29.52
   ],
   [
    -83.41,
    29.59
   ],
   [
    -83.41,
    29.63
   ],
   [
    -83.4,
    29.66
   ],
   [
    -83.47,
    29.69
   ],
   [
    -83.51,
    29.71
   ],
   [
    -83.55,
    29.75
   ],
   [
    -83.57,
    29.78
   ],
   [
    -83.6,
    29.83
   ],
   [
    -83.63,
    29.88
   ],
   [
    -83.66,
    29.9
   ],
   [
    -83.69,
    29.93
   ],
   [
    -83.73,
    29.94
   ],
   [
    -83.75,
    29.97
   ],
   [
    -83.78,
    29.98
   ],
   [
    -83.84,
    29.99
   ],
   [
    -83.88,
    30.02
   ],
   [
    -83.95,
    30.05
   ],
   [
    -83.98,
    30.09
   ],
   [
    -84.0,
    30.11
   ],
   [
    -84.03,
    30.11
   ],
   [
    -84.07,
    30.1
   ],
   [
    -84.12,
    30.08
   ],
   [
    -84.16,
    30.07
   ],
   [
    -84.21,
    30.1
   ],
   [
    -84.26,
    30.11
   ],
   [
    -84.3,
    30.06
   ],
   [
    -84.33,
    30.08
   ],
   [
    -84.36,
    30.06
   ],
   [
    -84.38,
    30.04
   ],
   [
    -84.39,
    30.01
   ],
   [
    -84.37,
    30.01
   ],
   [
    -84.37,
    29.97
   ],
   [
    -84.43,
    30.0
   ],
   [
    -84.44,
    29.98
   ],
   [
    -84.34,
    29.94
   ],
   [
    -84.38,
    29.91
   ],
   [
    -84.47,
    29.92
   ],
   [
    -84.52,
    29.92
   ],
   [
    -84.56,
    29.89
   ],
   [
    -84.62,
    29.87
   ],
   [
    -84.66,
    29.84
   ],
   [
    -84.75,
    29.8
   ],
   [
    -84.81,
    29.76
   ],
   [
    -84.92,
    29.73
   ],
   [
    -84.88,
    29.77
   ],
   [
    -84.86,
    29.8
   ],
   [
    -84.91,
    29.79
   ],
   [
    -84.94,
    29.75
   ],
   [
    -84.99,
    29.71
   ],
   [
    -85.16,
    29.71
   ],
   [
    -85.26,
    29.69
   ],
   [
    -85.31,
    29.77
   ],
   [
    -85.32,
    29.83
   ],
   [
    -85.34,
    29.87
   ],
   [
    -85.4,
    29.93
   ],
   [
    -85.48,
    29.98
   ],
   [
    -85.52,
    30.0
   ],
   [
    -85.56,
    30.03
   ],
   [
    -85.59,
    30.06
   ],
   [
    -85.62,
    30.06
   ],
   [
    -85.65,
    30.1
   ]
  ],
  "alerts": [
   {
    "event": "Hurricane Warning",
    "sender": "NWS Tallahassee FL",
    "issued": "2018-10-08T21:42Z"
   },
   {
    "event": "Flash Flood Watch",
    "sender": "NWS Tallahassee FL",
    "issued": "2018-10-10T00:00Z"
   }
  ],
  "bullets": [
   "In effect here: Hurricane Warning, Flash Flood Watch",
   "USDA NRCS \u00b7 serves Calhoun; Franklin; Gulf; Liberty",
   "Phone: (850) 674-8271"
  ]
 },
 {
  "id": "calhoun-county-fsa",
  "name": "Calhoun County FSA",
  "short": "Calhoun FSA",
  "lat": 30.443,
  "lon": -85.047,
  "address": "17413 NW Leonard Street, Blountstown, FL 32424",
  "agency": "USDA FSA",
  "phone": "(850) 674-8388",
  "countiesServed": "Calhoun",
  "permanentStatus": "open",
  "operatingStatus": "open",
  "source": {
   "name": "Florida NRCS/FSA Service Center Contact List",
   "url": "https://www.nrcs.usda.gov/sites/default/files/2024-08/Florida-NRCS-FSA-Service-Center-Contact-List-FINAL-FINAL_Aug2024.pdf",
   "date": "2024-06-21"
  },
  "total": null,
  "affected": null,
  "opinion": null,
  "reasoning": null,
  "email": null,
  "status": "unknown",
  "alert": {
   "type": "hurricane",
   "title": "Hurricane Warning",
   "area": "Covers this office (Calhoun)",
   "expires": "end time not in NWS archive",
   "source": "NWS Tallahassee FL"
  },
  "alertPolygon": [
   [
    -85.68,
    30.11
   ],
   [
    -85.67,
    30.14
   ],
   [
    -85.62,
    30.09
   ],
   [
    -85.56,
    30.09
   ],
   [
    -85.53,
    30.06
   ],
   [
    -85.5,
    30.03
   ],
   [
    -85.42,
    30.04
   ],
   [
    -85.43,
    30.05
   ],
   [
    -85.45,
    30.03
   ],
   [
    -85.51,
    30.09
   ],
   [
    -85.53,
    30.12
   ],
   [
    -85.57,
    30.12
   ],
   [
    -85.64,
    30.14
   ],
   [
    -85.71,
    30.17
   ],
   [
    -85.72,
    30.2
   ],
   [
    -85.69,
    30.22
   ],
   [
    -85.62,
    30.26
   ],
   [
    -85.59,
    30.29
   ],
   [
    -85.58,
    30.33
   ],
   [
    -85.63,
    30.28
   ],
   [
    -85.67,
    30.27
   ],
   [
    -85.72,
    30.24
   ],
   [
    -85.75,
    30.29
   ],
   [
    -85.8,
    30.29
   ],
   [
    -85.85,
    30.28
   ],
   [
    -85.85,
    30.23
   ],
   [
    -85.79,
    30.25
   ],
   [
    -85.76,
    30.24
   ],
   [
    -85.76,
    30.21
   ],
   [
    -85.75,
    30.2
   ],
   [
    -85.74,
    30.16
   ],
   [
    -85.73,
    30.14
   ],
   [
    -85.78,
    30.16
   ],
   [
    -85.84,
    30.2
   ],
   [
    -85.9,
    30.22
   ],
   [
    -85.95,
    30.25
   ],
   [
    -86.04,
    30.28
   ],
   [
    -86.13,
    30.32
   ],
   [
    -86.23,
    30.34
   ],
   [
    -86.32,
    30.37
   ],
   [
    -86.38,
    30.39
   ],
   [
    -86.3,
    30.41
   ],
   [
    -86.24,
    30.4
   ],
   [
    -86.26,
    30.42
   ],
   [
    -86.22,
    30.41
   ],
   [
    -86.17,
    30.39
   ],
   [
    -86.12,
    30.43
   ],
   [
    -86.14,
    30.46
   ],
   [
    -86.19,
    30.46
   ],
   [
    -86.22,
    30.48
   ],
   [
    -86.25,
    30.49
   ],
   [
    -86.3,
    30.47
   ],
   [
    -86.39,
    30.99
   ],
   [
    -86.12,
    31.18
   ],
   [
    -85.7,
    31.21
   ],
   [
    -85.67,
    31.27
   ],
   [
    -85.59,
    31.27
   ],
   [
    -85.49,
    31.29
   ],
   [
    -85.08,
    31.32
   ],
   [
    -85.08,
    31.43
   ],
   [
    -85.05,
    31.5
   ],
   [
    -84.97,
    31.5
   ],
   [
    -84.81,
    31.49
   ],
   [
    -84.79,
    31.44
   ],
   [
    -84.53,
    31.44
   ],
   [
    -84.51,
    31.43
   ],
   [
    -84.44,
    31.45
   ],
   [
    -83.76,
    31.32
   ],
   [
    -83.52,
    31.3
   ],
   [
    -83.53,
    31.19
   ],
   [
    -83.55,
    31.14
   ],
   [
    -83.58,
    31.08
   ],
   [
    -83.55,
    31.06
   ],
   [
    -83.47,
    31.01
   ],
   [
    -83.43,
    30.96
   ],
   [
    -83.43,
    30.89
   ],
   [
    -83.36,
    30.88
   ],
   [
    -83.38,
    30.83
   ],
   [
    -83.44,
    30.81
   ],
   [
    -83.46,
    30.76
   ],
   [
    -83.46,
    30.71
   ],
   [
    -83.42,
    30.69
   ],
   [
    -83.4,
    30.68
   ],
   [
    -83.5,
    30.65
   ],
   [
    -83.61,
    30.58
   ],
   [
    -83.67,
    30.55
   ],
   [
    -83.73,
    30.51
   ],
   [
    -83.72,
    30.47
   ],
   [
    -83.73,
    30.42
   ],
   [
    -83.79,
    30.39
   ],
   [
    -83.8,
    30.35
   ],
   [
    -83.82,
    30.3
   ],
   [
    -83.9,
    30.25
   ],
   [
    -83.93,
    30.19
   ],
   [
    -83.51,
    29.85
   ],
   [
    -82.99,
    29.47
   ],
   [
    -83.02,
    29.43
   ],
   [
    -83.03,
    29.39
   ],
   [
    -83.06,
    29.36
   ],
   [
    -83.08,
    29.34
   ],
   [
    -83.11,
    29.33
   ],
   [
    -83.17,
    29.3
   ],
   [
    -83.17,
    29.34
   ],
   [
    -83.18,
    29.37
   ],
   [
    -83.2,
    29.4
   ],
   [
    -83.26,
    29.43
   ],
   [
    -83.29,
    29.44
   ],
   [
    -83.31,
    29.47
   ],
   [
    -83.35,
    29.49
   ],
   [
    -83.39,
    29.52
   ],
   [
    -83.41,
    29.59
   ],
   [
    -83.41,
    29.63
   ],
   [
    -83.4,
    29.66
   ],
   [
    -83.47,
    29.69
   ],
   [
    -83.51,
    29.71
   ],
   [
    -83.55,
    29.75
   ],
   [
    -83.57,
    29.78
   ],
   [
    -83.6,
    29.83
   ],
   [
    -83.63,
    29.88
   ],
   [
    -83.66,
    29.9
   ],
   [
    -83.69,
    29.93
   ],
   [
    -83.73,
    29.94
   ],
   [
    -83.75,
    29.97
   ],
   [
    -83.78,
    29.98
   ],
   [
    -83.84,
    29.99
   ],
   [
    -83.88,
    30.02
   ],
   [
    -83.95,
    30.05
   ],
   [
    -83.98,
    30.09
   ],
   [
    -84.0,
    30.11
   ],
   [
    -84.03,
    30.11
   ],
   [
    -84.07,
    30.1
   ],
   [
    -84.12,
    30.08
   ],
   [
    -84.16,
    30.07
   ],
   [
    -84.21,
    30.1
   ],
   [
    -84.26,
    30.11
   ],
   [
    -84.3,
    30.06
   ],
   [
    -84.33,
    30.08
   ],
   [
    -84.36,
    30.06
   ],
   [
    -84.38,
    30.04
   ],
   [
    -84.39,
    30.01
   ],
   [
    -84.37,
    30.01
   ],
   [
    -84.37,
    29.97
   ],
   [
    -84.43,
    30.0
   ],
   [
    -84.44,
    29.98
   ],
   [
    -84.34,
    29.94
   ],
   [
    -84.38,
    29.91
   ],
   [
    -84.47,
    29.92
   ],
   [
    -84.52,
    29.92
   ],
   [
    -84.56,
    29.89
   ],
   [
    -84.62,
    29.87
   ],
   [
    -84.66,
    29.84
   ],
   [
    -84.75,
    29.8
   ],
   [
    -84.81,
    29.76
   ],
   [
    -84.92,
    29.73
   ],
   [
    -84.88,
    29.77
   ],
   [
    -84.86,
    29.8
   ],
   [
    -84.91,
    29.79
   ],
   [
    -84.94,
    29.75
   ],
   [
    -84.99,
    29.71
   ],
   [
    -85.16,
    29.71
   ],
   [
    -85.26,
    29.69
   ],
   [
    -85.31,
    29.77
   ],
   [
    -85.32,
    29.83
   ],
   [
    -85.34,
    29.87
   ],
   [
    -85.4,
    29.93
   ],
   [
    -85.48,
    29.98
   ],
   [
    -85.52,
    30.0
   ],
   [
    -85.56,
    30.03
   ],
   [
    -85.59,
    30.06
   ],
   [
    -85.62,
    30.06
   ],
   [
    -85.65,
    30.1
   ]
  ],
  "alerts": [
   {
    "event": "Hurricane Warning",
    "sender": "NWS Tallahassee FL",
    "issued": "2018-10-08T21:42Z"
   },
   {
    "event": "Flash Flood Watch",
    "sender": "NWS Tallahassee FL",
    "issued": "2018-10-10T00:00Z"
   }
  ],
  "bullets": [
   "In effect here: Hurricane Warning, Flash Flood Watch",
   "USDA FSA \u00b7 serves Calhoun",
   "Phone: (850) 674-8388"
  ]
 },
 {
  "id": "sarasota-service-center",
  "name": "Sarasota Service Center",
  "short": "Sarasota",
  "lat": 27.385,
  "lon": -82.45,
  "address": "6942 Professional Parkway, Sarasota, FL 34240",
  "agency": "USDA NRCS",
  "phone": "(941) 907-0011",
  "countiesServed": "Charlotte; Manatee; Sarasota",
  "permanentStatus": "open",
  "operatingStatus": "open",
  "source": {
   "name": "Florida NRCS/FSA Service Center Contact List",
   "url": "https://www.nrcs.usda.gov/sites/default/files/2024-08/Florida-NRCS-FSA-Service-Center-Contact-List-FINAL-FINAL_Aug2024.pdf",
   "date": "2024-06-21"
  },
  "total": null,
  "affected": null,
  "opinion": null,
  "reasoning": null,
  "email": null,
  "status": "normal",
  "alert": null,
  "alertPolygon": null,
  "alerts": [],
  "bullets": [
   "No Hurricane Michael warnings covered this office",
   "USDA NRCS \u00b7 serves Charlotte; Manatee; Sarasota",
   "Phone: (941) 907-0011"
  ]
 },
 {
  "id": "fort-myers-service-center",
  "name": "Fort Myers Service Center",
  "short": "Fort Myers",
  "lat": 26.672,
  "lon": -81.903,
  "address": "3434 Hancock Bridge Parkway, Fort Myers, FL 33903",
  "agency": "USDA NRCS",
  "phone": "(239) 997-7331",
  "countiesServed": "Collier; Lee",
  "permanentStatus": "open",
  "operatingStatus": "open",
  "source": {
   "name": "Florida NRCS/FSA Service Center Contact List",
   "url": "https://www.nrcs.usda.gov/sites/default/files/2024-08/Florida-NRCS-FSA-Service-Center-Contact-List-FINAL-FINAL_Aug2024.pdf",
   "date": "2024-06-21"
  },
  "total": null,
  "affected": null,
  "opinion": null,
  "reasoning": null,
  "email": null,
  "status": "normal",
  "alert": null,
  "alertPolygon": null,
  "alerts": [],
  "bullets": [
   "No Hurricane Michael warnings covered this office",
   "USDA NRCS \u00b7 serves Collier; Lee",
   "Phone: (239) 997-7331"
  ]
 },
 {
  "id": "lee-county-fsa",
  "name": "Lee County FSA",
  "short": "Lee FSA",
  "lat": 26.672,
  "lon": -81.903,
  "address": "3434 Hancock Bridge Parkway, Fort Myers, FL 33903",
  "agency": "USDA FSA",
  "phone": "(239) 997-7331",
  "countiesServed": "Lee",
  "permanentStatus": "open",
  "operatingStatus": "open",
  "source": {
   "name": "Florida NRCS/FSA Service Center Contact List",
   "url": "https://www.nrcs.usda.gov/sites/default/files/2024-08/Florida-NRCS-FSA-Service-Center-Contact-List-FINAL-FINAL_Aug2024.pdf",
   "date": "2024-06-21"
  },
  "total": null,
  "affected": null,
  "opinion": null,
  "reasoning": null,
  "email": null,
  "status": "normal",
  "alert": null,
  "alertPolygon": null,
  "alerts": [],
  "bullets": [
   "No Hurricane Michael warnings covered this office",
   "USDA FSA \u00b7 serves Lee",
   "Phone: (239) 997-7331"
  ]
 },
 {
  "id": "ocala-service-center",
  "name": "Ocala Service Center",
  "short": "Ocala",
  "lat": 29.189,
  "lon": -82.11,
  "address": "2441 NE 3rd Street, Suite 204-2, Ocala, FL 34470",
  "agency": "USDA NRCS",
  "phone": "(352) 732-7534",
  "countiesServed": "Citrus; Marion",
  "permanentStatus": "open",
  "operatingStatus": "open",
  "source": {
   "name": "Florida NRCS/FSA Service Center Contact List",
   "url": "https://www.nrcs.usda.gov/sites/default/files/2024-08/Florida-NRCS-FSA-Service-Center-Contact-List-FINAL-FINAL_Aug2024.pdf",
   "date": "2024-06-21"
  },
  "total": null,
  "affected": null,
  "opinion": null,
  "reasoning": null,
  "email": null,
  "status": "normal",
  "alert": null,
  "alertPolygon": null,
  "alerts": [],
  "bullets": [
   "No Hurricane Michael warnings covered this office",
   "USDA NRCS \u00b7 serves Citrus; Marion",
   "Phone: (352) 732-7534"
  ]
 },
 {
  "id": "sumter-county-fsa",
  "name": "Sumter County FSA",
  "short": "Sumter FSA",
  "lat": 28.665,
  "lon": -82.113,
  "address": "7620 State Road 471, Suite 3, Bushnell, FL 33513",
  "agency": "USDA FSA",
  "phone": "(352) 793-2651",
  "countiesServed": "Sumter",
  "permanentStatus": "open",
  "operatingStatus": "open",
  "source": {
   "name": "Florida NRCS/FSA Service Center Contact List",
   "url": "https://www.nrcs.usda.gov/sites/default/files/2024-08/Florida-NRCS-FSA-Service-Center-Contact-List-FINAL-FINAL_Aug2024.pdf",
   "date": "2024-06-21"
  },
  "total": null,
  "affected": null,
  "opinion": null,
  "reasoning": null,
  "email": null,
  "status": "normal",
  "alert": null,
  "alertPolygon": null,
  "alerts": [],
  "bullets": [
   "No Hurricane Michael warnings covered this office",
   "USDA FSA \u00b7 serves Sumter",
   "Phone: (352) 793-2651"
  ]
 },
 {
  "id": "east-palatka-service-center",
  "name": "East Palatka Service Center",
  "short": "East Palatka",
  "lat": 29.655,
  "lon": -81.597,
  "address": "111 Yelvington Road, East Palatka, FL 32131",
  "agency": "USDA NRCS",
  "phone": "(386) 328-5051",
  "countiesServed": "Clay; Putnam; St. Johns",
  "permanentStatus": "open",
  "operatingStatus": "open",
  "source": {
   "name": "Florida NRCS/FSA Service Center Contact List",
   "url": "https://www.nrcs.usda.gov/sites/default/files/2024-08/Florida-NRCS-FSA-Service-Center-Contact-List-FINAL-FINAL_Aug2024.pdf",
   "date": "2024-06-21"
  },
  "total": null,
  "affected": null,
  "opinion": null,
  "reasoning": null,
  "email": null,
  "status": "normal",
  "alert": null,
  "alertPolygon": null,
  "alerts": [],
  "bullets": [
   "No Hurricane Michael warnings covered this office",
   "USDA NRCS \u00b7 serves Clay; Putnam; St. Johns",
   "Phone: (386) 328-5051"
  ]
 },
 {
  "id": "lake-city-service-center",
  "name": "Lake City Service Center",
  "short": "Lake City",
  "lat": 30.17,
  "lon": -82.64,
  "address": "2304 SW Main Boulevard, Lake City, FL 32025",
  "agency": "USDA NRCS",
  "phone": "(386) 752-8447",
  "countiesServed": "Columbia",
  "permanentStatus": "open",
  "operatingStatus": "open",
  "source": {
   "name": "Florida NRCS/FSA Service Center Contact List",
   "url": "https://www.nrcs.usda.gov/sites/default/files/2024-08/Florida-NRCS-FSA-Service-Center-Contact-List-FINAL-FINAL_Aug2024.pdf",
   "date": "2024-06-21"
  },
  "total": null,
  "affected": null,
  "opinion": null,
  "reasoning": null,
  "email": null,
  "status": "normal",
  "alert": null,
  "alertPolygon": null,
  "alerts": [],
  "bullets": [
   "No Hurricane Michael warnings covered this office",
   "USDA NRCS \u00b7 serves Columbia",
   "Phone: (386) 752-8447"
  ]
 },
 {
  "id": "wauchula-service-center",
  "name": "Wauchula Service Center",
  "short": "Wauchula",
  "lat": 27.547,
  "lon": -81.811,
  "address": "316 North 7th Avenue, Wauchula, FL 33873",
  "agency": "USDA NRCS",
  "phone": "(863) 773-4764",
  "countiesServed": "De Soto; Hardee",
  "permanentStatus": "open",
  "operatingStatus": "open",
  "source": {
   "name": "Florida NRCS/FSA Service Center Contact List",
   "url": "https://www.nrcs.usda.gov/sites/default/files/2024-08/Florida-NRCS-FSA-Service-Center-Contact-List-FINAL-FINAL_Aug2024.pdf",
   "date": "2024-06-21"
  },
  "total": null,
  "affected": null,
  "opinion": null,
  "reasoning": null,
  "email": null,
  "status": "normal",
  "alert": null,
  "alertPolygon": null,
  "alerts": [],
  "bullets": [
   "No Hurricane Michael warnings covered this office",
   "USDA NRCS \u00b7 serves De Soto; Hardee",
   "Phone: (863) 773-4764"
  ]
 },
 {
  "id": "trenton-service-center",
  "name": "Trenton Service Center",
  "short": "Trenton",
  "lat": 29.613,
  "lon": -82.817,
  "address": "1727 East Wade Street, Trenton, FL 32693",
  "agency": "USDA NRCS",
  "phone": "(352) 658-4059",
  "countiesServed": "Dixie; Levy; Gilchrist",
  "permanentStatus": "open",
  "operatingStatus": "open",
  "source": {
   "name": "Florida NRCS/FSA Service Center Contact List",
   "url": "https://www.nrcs.usda.gov/sites/default/files/2024-08/Florida-NRCS-FSA-Service-Center-Contact-List-FINAL-FINAL_Aug2024.pdf",
   "date": "2024-06-21"
  },
  "total": null,
  "affected": null,
  "opinion": null,
  "reasoning": null,
  "email": null,
  "status": "normal",
  "alert": null,
  "alertPolygon": null,
  "alerts": [],
  "bullets": [
   "No Hurricane Michael warnings covered this office",
   "USDA NRCS \u00b7 serves Dixie; Levy; Gilchrist",
   "Phone: (352) 658-4059"
  ]
 },
 {
  "id": "molino-service-center",
  "name": "Molino Service Center",
  "short": "Molino",
  "lat": 30.723,
  "lon": -87.316,
  "address": "151 Highway 97, Molino, FL 32577-5553",
  "agency": "USDA NRCS",
  "phone": "(850) 587-5404",
  "countiesServed": "Escambia",
  "permanentStatus": "open",
  "operatingStatus": "open",
  "source": {
   "name": "Florida NRCS/FSA Service Center Contact List",
   "url": "https://www.nrcs.usda.gov/sites/default/files/2024-08/Florida-NRCS-FSA-Service-Center-Contact-List-FINAL-FINAL_Aug2024.pdf",
   "date": "2024-06-21"
  },
  "total": null,
  "affected": null,
  "opinion": null,
  "reasoning": null,
  "email": null,
  "status": "unknown",
  "alert": {
   "type": "hurricane",
   "title": "Tropical Storm Warning",
   "area": "Covers this office (Escambia)",
   "expires": "end time not in NWS archive",
   "source": "NWS Mobile AL"
  },
  "alertPolygon": [
   [
    -87.84,
    30.38
   ],
   [
    -87.88,
    30.39
   ],
   [
    -87.9,
    30.4
   ],
   [
    -87.91,
    30.41
   ],
   [
    -87.92,
    30.45
   ],
   [
    -87.94,
    30.48
   ],
   [
    -87.93,
    30.5
   ],
   [
    -87.92,
    30.52
   ],
   [
    -87.91,
    30.54
   ],
   [
    -87.9,
    30.57
   ],
   [
    -87.91,
    30.62
   ],
   [
    -87.92,
    30.64
   ],
   [
    -87.93,
    30.65
   ],
   [
    -87.92,
    30.69
   ],
   [
    -87.91,
    30.71
   ],
   [
    -87.92,
    30.72
   ],
   [
    -87.93,
    30.71
   ],
   [
    -87.95,
    30.7
   ],
   [
    -87.97,
    30.73
   ],
   [
    -87.98,
    30.71
   ],
   [
    -88.0,
    30.72
   ],
   [
    -88.01,
    30.74
   ],
   [
    -87.98,
    30.75
   ],
   [
    -87.99,
    30.77
   ],
   [
    -88.0,
    30.78
   ],
   [
    -87.97,
    30.79
   ],
   [
    -87.96,
    30.78
   ],
   [
    -87.56,
    30.79
   ],
   [
    -87.59,
    30.81
   ],
   [
    -87.6,
    30.82
   ],
   [
    -87.62,
    30.83
   ],
   [
    -87.63,
    30.85
   ],
   [
    -87.62,
    30.88
   ],
   [
    -87.61,
    30.91
   ],
   [
    -87.6,
    30.93
   ],
   [
    -87.59,
    30.95
   ],
   [
    -87.6,
    30.99
   ],
   [
    -87.62,
    31.0
   ],
   [
    -87.58,
    31.24
   ],
   [
    -87.54,
    31.23
   ],
   [
    -87.53,
    31.24
   ],
   [
    -87.5,
    31.25
   ],
   [
    -87.43,
    31.26
   ],
   [
    -87.42,
    31.27
   ],
   [
    -87.41,
    31.28
   ],
   [
    -87.4,
    31.29
   ],
   [
    -87.37,
    31.31
   ],
   [
    -87.36,
    31.33
   ],
   [
    -87.35,
    31.35
   ],
   [
    -87.32,
    31.38
   ],
   [
    -87.31,
    31.39
   ],
   [
    -87.27,
    31.41
   ],
   [
    -87.25,
    31.43
   ],
   [
    -87.24,
    31.44
   ],
   [
    -87.23,
    31.45
   ],
   [
    -87.2,
    31.46
   ],
   [
    -87.19,
    31.48
   ],
   [
    -87.18,
    31.49
   ],
   [
    -87.16,
    31.55
   ],
   [
    -87.15,
    31.58
   ],
   [
    -87.14,
    31.59
   ],
   [
    -87.09,
    31.65
   ],
   [
    -87.08,
    31.66
   ],
   [
    -87.06,
    31.67
   ],
   [
    -87.05,
    31.71
   ],
   [
    -87.04,
    31.72
   ],
   [
    -87.01,
    31.71
   ],
   [
    -86.98,
    31.72
   ],
   [
    -86.95,
    31.73
   ],
   [
    -86.94,
    31.74
   ],
   [
    -86.91,
    31.75
   ],
   [
    -86.9,
    31.63
   ],
   [
    -86.89,
    31.61
   ],
   [
    -86.88,
    31.59
   ],
   [
    -86.87,
    31.58
   ],
   [
    -86.86,
    31.55
   ],
   [
    -86.85,
    31.54
   ],
   [
    -86.82,
    31.53
   ],
   [
    -86.51,
    31.52
   ],
   [
    -86.4,
    31.53
   ],
   [
    -86.39,
    31.45
   ],
   [
    -86.38,
    31.46
   ],
   [
    -86.37,
    31.47
   ],
   [
    -86.36,
    31.48
   ],
   [
    -86.33,
    31.49
   ],
   [
    -86.32,
    31.5
   ],
   [
    -86.31,
    31.51
   ],
   [
    -86.3,
    31.52
   ],
   [
    -86.28,
    31.53
   ],
   [
    -86.26,
    31.46
   ],
   [
    -86.19,
    31.44
   ],
   [
    -86.19,
    31.25
   ],
   [
    -86.55,
    30.99
   ],
   [
    -86.59,
    30.99
   ],
   [
    -86.69,
    31.0
   ],
   [
    -86.71,
    30.99
   ],
   [
    -86.79,
    31.0
   ],
   [
    -86.8,
    30.62
   ],
   [
    -86.82,
    30.44
   ],
   [
    -86.97,
    30.5
   ],
   [
    -86.92,
    30.56
   ],
   [
    -86.98,
    30.6
   ],
   [
    -86.99,
    30.61
   ],
   [
    -87.03,
    30.62
   ],
   [
    -87.04,
    30.63
   ],
   [
    -87.06,
    30.63
   ],
   [
    -87.07,
    30.6
   ],
   [
    -87.04,
    30.58
   ],
   [
    -87.09,
    30.57
   ],
   [
    -87.14,
    30.58
   ],
   [
    -87.27,
    30.61
   ],
   [
    -87.37,
    30.56
   ],
   [
    -87.44,
    30.52
   ],
   [
    -87.45,
    30.51
   ],
   [
    -87.44,
    30.5
   ],
   [
    -87.43,
    30.46
   ],
   [
    -87.42,
    30.45
   ],
   [
    -87.39,
    30.44
   ],
   [
    -87.4,
    30.42
   ],
   [
    -87.43,
    30.41
   ],
   [
    -87.44,
    30.4
   ],
   [
    -87.45,
    30.38
   ],
   [
    -87.46,
    30.36
   ],
   [
    -87.47,
    30.35
   ],
   [
    -87.49,
    30.34
   ],
   [
    -87.5,
    30.35
   ],
   [
    -87.51,
    30.34
   ],
   [
    -87.52,
    30.33
   ],
   [
    -87.53,
    30.32
   ],
   [
    -87.54,
    30.33
   ],
   [
    -87.55,
    30.31
   ],
   [
    -87.56,
    30.32
   ],
   [
    -87.57,
    30.31
   ],
   [
    -87.54,
    30.3
   ],
   [
    -87.55,
    30.29
   ],
   [
    -87.57,
    30.27
   ],
   [
    -87.58,
    30.28
   ],
   [
    -87.59,
    30.27
   ],
   [
    -87.64,
    30.26
   ],
   [
    -87.69,
    30.25
   ],
   [
    -87.71,
    30.26
   ],
   [
    -87.7,
    30.25
   ],
   [
    -87.73,
    30.24
   ],
   [
    -87.78,
    30.25
   ],
   [
    -87.79,
    30.24
   ],
   [
    -87.8,
    30.23
   ],
   [
    -87.82,
    30.24
   ],
   [
    -87.97,
    30.23
   ],
   [
    -87.96,
    30.24
   ],
   [
    -87.95,
    30.25
   ],
   [
    -87.93,
    30.26
   ],
   [
    -87.91,
    30.25
   ],
   [
    -87.85,
    30.24
   ],
   [
    -87.79,
    30.25
   ],
   [
    -87.76,
    30.26
   ],
   [
    -87.75,
    30.28
   ],
   [
    -87.76,
    30.29
   ],
   [
    -87.78,
    30.31
   ],
   [
    -87.8,
    30.32
   ],
   [
    -87.81,
    30.33
   ],
   [
    -87.82,
    30.34
   ],
   [
    -87.83,
    30.36
   ],
   [
    -87.83,
    30.37
   ],
   [
    -87.82,
    30.39
   ],
   [
    -87.83,
    30.43
   ],
   [
    -87.84,
    30.41
   ],
   [
    -87.85,
    30.4
   ],
   [
    -87.84,
    30.39
   ]
  ],
  "alerts": [
   {
    "event": "Tropical Storm Warning",
    "sender": "NWS Mobile AL",
    "issued": "2018-10-08T21:29Z"
   }
  ],
  "bullets": [
   "In effect here: Tropical Storm Warning",
   "USDA NRCS \u00b7 serves Escambia",
   "Phone: (850) 587-5404"
  ]
 },
 {
  "id": "santa-rosa-county-fsa",
  "name": "Santa Rosa County FSA",
  "short": "Santa Rosa FSA",
  "lat": 30.954,
  "lon": -87.151,
  "address": "3927 Highway 4, Jay, FL 32565-1752",
  "agency": "USDA FSA",
  "phone": "(850) 675-6696",
  "countiesServed": "Santa Rosa",
  "permanentStatus": "open",
  "operatingStatus": "open",
  "source": {
   "name": "Florida NRCS/FSA Service Center Contact List",
   "url": "https://www.nrcs.usda.gov/sites/default/files/2024-08/Florida-NRCS-FSA-Service-Center-Contact-List-FINAL-FINAL_Aug2024.pdf",
   "date": "2024-06-21"
  },
  "total": null,
  "affected": null,
  "opinion": null,
  "reasoning": null,
  "email": null,
  "status": "unknown",
  "alert": {
   "type": "hurricane",
   "title": "Tropical Storm Warning",
   "area": "Covers this office (Santa Rosa)",
   "expires": "end time not in NWS archive",
   "source": "NWS Mobile AL"
  },
  "alertPolygon": [
   [
    -87.84,
    30.38
   ],
   [
    -87.88,
    30.39
   ],
   [
    -87.9,
    30.4
   ],
   [
    -87.91,
    30.41
   ],
   [
    -87.92,
    30.45
   ],
   [
    -87.94,
    30.48
   ],
   [
    -87.93,
    30.5
   ],
   [
    -87.92,
    30.52
   ],
   [
    -87.91,
    30.54
   ],
   [
    -87.9,
    30.57
   ],
   [
    -87.91,
    30.62
   ],
   [
    -87.92,
    30.64
   ],
   [
    -87.93,
    30.65
   ],
   [
    -87.92,
    30.69
   ],
   [
    -87.91,
    30.71
   ],
   [
    -87.92,
    30.72
   ],
   [
    -87.93,
    30.71
   ],
   [
    -87.95,
    30.7
   ],
   [
    -87.97,
    30.73
   ],
   [
    -87.98,
    30.71
   ],
   [
    -88.0,
    30.72
   ],
   [
    -88.01,
    30.74
   ],
   [
    -87.98,
    30.75
   ],
   [
    -87.99,
    30.77
   ],
   [
    -88.0,
    30.78
   ],
   [
    -87.97,
    30.79
   ],
   [
    -87.96,
    30.78
   ],
   [
    -87.56,
    30.79
   ],
   [
    -87.59,
    30.81
   ],
   [
    -87.6,
    30.82
   ],
   [
    -87.62,
    30.83
   ],
   [
    -87.63,
    30.85
   ],
   [
    -87.62,
    30.88
   ],
   [
    -87.61,
    30.91
   ],
   [
    -87.6,
    30.93
   ],
   [
    -87.59,
    30.95
   ],
   [
    -87.6,
    30.99
   ],
   [
    -87.62,
    31.0
   ],
   [
    -87.58,
    31.24
   ],
   [
    -87.54,
    31.23
   ],
   [
    -87.53,
    31.24
   ],
   [
    -87.5,
    31.25
   ],
   [
    -87.43,
    31.26
   ],
   [
    -87.42,
    31.27
   ],
   [
    -87.41,
    31.28
   ],
   [
    -87.4,
    31.29
   ],
   [
    -87.37,
    31.31
   ],
   [
    -87.36,
    31.33
   ],
   [
    -87.35,
    31.35
   ],
   [
    -87.32,
    31.38
   ],
   [
    -87.31,
    31.39
   ],
   [
    -87.27,
    31.41
   ],
   [
    -87.25,
    31.43
   ],
   [
    -87.24,
    31.44
   ],
   [
    -87.23,
    31.45
   ],
   [
    -87.2,
    31.46
   ],
   [
    -87.19,
    31.48
   ],
   [
    -87.18,
    31.49
   ],
   [
    -87.16,
    31.55
   ],
   [
    -87.15,
    31.58
   ],
   [
    -87.14,
    31.59
   ],
   [
    -87.09,
    31.65
   ],
   [
    -87.08,
    31.66
   ],
   [
    -87.06,
    31.67
   ],
   [
    -87.05,
    31.71
   ],
   [
    -87.04,
    31.72
   ],
   [
    -87.01,
    31.71
   ],
   [
    -86.98,
    31.72
   ],
   [
    -86.95,
    31.73
   ],
   [
    -86.94,
    31.74
   ],
   [
    -86.91,
    31.75
   ],
   [
    -86.9,
    31.63
   ],
   [
    -86.89,
    31.61
   ],
   [
    -86.88,
    31.59
   ],
   [
    -86.87,
    31.58
   ],
   [
    -86.86,
    31.55
   ],
   [
    -86.85,
    31.54
   ],
   [
    -86.82,
    31.53
   ],
   [
    -86.51,
    31.52
   ],
   [
    -86.4,
    31.53
   ],
   [
    -86.39,
    31.45
   ],
   [
    -86.38,
    31.46
   ],
   [
    -86.37,
    31.47
   ],
   [
    -86.36,
    31.48
   ],
   [
    -86.33,
    31.49
   ],
   [
    -86.32,
    31.5
   ],
   [
    -86.31,
    31.51
   ],
   [
    -86.3,
    31.52
   ],
   [
    -86.28,
    31.53
   ],
   [
    -86.26,
    31.46
   ],
   [
    -86.19,
    31.44
   ],
   [
    -86.19,
    31.25
   ],
   [
    -86.55,
    30.99
   ],
   [
    -86.59,
    30.99
   ],
   [
    -86.69,
    31.0
   ],
   [
    -86.71,
    30.99
   ],
   [
    -86.79,
    31.0
   ],
   [
    -86.8,
    30.62
   ],
   [
    -86.82,
    30.44
   ],
   [
    -86.97,
    30.5
   ],
   [
    -86.92,
    30.56
   ],
   [
    -86.98,
    30.6
   ],
   [
    -86.99,
    30.61
   ],
   [
    -87.03,
    30.62
   ],
   [
    -87.04,
    30.63
   ],
   [
    -87.06,
    30.63
   ],
   [
    -87.07,
    30.6
   ],
   [
    -87.04,
    30.58
   ],
   [
    -87.09,
    30.57
   ],
   [
    -87.14,
    30.58
   ],
   [
    -87.27,
    30.61
   ],
   [
    -87.37,
    30.56
   ],
   [
    -87.44,
    30.52
   ],
   [
    -87.45,
    30.51
   ],
   [
    -87.44,
    30.5
   ],
   [
    -87.43,
    30.46
   ],
   [
    -87.42,
    30.45
   ],
   [
    -87.39,
    30.44
   ],
   [
    -87.4,
    30.42
   ],
   [
    -87.43,
    30.41
   ],
   [
    -87.44,
    30.4
   ],
   [
    -87.45,
    30.38
   ],
   [
    -87.46,
    30.36
   ],
   [
    -87.47,
    30.35
   ],
   [
    -87.49,
    30.34
   ],
   [
    -87.5,
    30.35
   ],
   [
    -87.51,
    30.34
   ],
   [
    -87.52,
    30.33
   ],
   [
    -87.53,
    30.32
   ],
   [
    -87.54,
    30.33
   ],
   [
    -87.55,
    30.31
   ],
   [
    -87.56,
    30.32
   ],
   [
    -87.57,
    30.31
   ],
   [
    -87.54,
    30.3
   ],
   [
    -87.55,
    30.29
   ],
   [
    -87.57,
    30.27
   ],
   [
    -87.58,
    30.28
   ],
   [
    -87.59,
    30.27
   ],
   [
    -87.64,
    30.26
   ],
   [
    -87.69,
    30.25
   ],
   [
    -87.71,
    30.26
   ],
   [
    -87.7,
    30.25
   ],
   [
    -87.73,
    30.24
   ],
   [
    -87.78,
    30.25
   ],
   [
    -87.79,
    30.24
   ],
   [
    -87.8,
    30.23
   ],
   [
    -87.82,
    30.24
   ],
   [
    -87.97,
    30.23
   ],
   [
    -87.96,
    30.24
   ],
   [
    -87.95,
    30.25
   ],
   [
    -87.93,
    30.26
   ],
   [
    -87.91,
    30.25
   ],
   [
    -87.85,
    30.24
   ],
   [
    -87.79,
    30.25
   ],
   [
    -87.76,
    30.26
   ],
   [
    -87.75,
    30.28
   ],
   [
    -87.76,
    30.29
   ],
   [
    -87.78,
    30.31
   ],
   [
    -87.8,
    30.32
   ],
   [
    -87.81,
    30.33
   ],
   [
    -87.82,
    30.34
   ],
   [
    -87.83,
    30.36
   ],
   [
    -87.83,
    30.37
   ],
   [
    -87.82,
    30.39
   ],
   [
    -87.83,
    30.43
   ],
   [
    -87.84,
    30.41
   ],
   [
    -87.85,
    30.4
   ],
   [
    -87.84,
    30.39
   ]
  ],
  "alerts": [
   {
    "event": "Tropical Storm Warning",
    "sender": "NWS Mobile AL",
    "issued": "2018-10-08T21:29Z"
   }
  ],
  "bullets": [
   "In effect here: Tropical Storm Warning",
   "USDA FSA \u00b7 serves Santa Rosa",
   "Phone: (850) 675-6696"
  ]
 },
 {
  "id": "deland-service-center",
  "name": "DeLand Service Center",
  "short": "DeLand",
  "lat": 29.028,
  "lon": -81.303,
  "address": "101 Heavensgate Road, Suite F, DeLand, FL 32720",
  "agency": "USDA NRCS",
  "phone": "(386) 985-4037 ext. 3",
  "countiesServed": "Flagler; Volusia",
  "permanentStatus": "open",
  "operatingStatus": "open",
  "source": {
   "name": "Florida NRCS/FSA Service Center Contact List",
   "url": "https://www.nrcs.usda.gov/sites/default/files/2024-08/Florida-NRCS-FSA-Service-Center-Contact-List-FINAL-FINAL_Aug2024.pdf",
   "date": "2024-06-21"
  },
  "total": null,
  "affected": null,
  "opinion": null,
  "reasoning": null,
  "email": null,
  "status": "normal",
  "alert": null,
  "alertPolygon": null,
  "alerts": [],
  "bullets": [
   "No Hurricane Michael warnings covered this office",
   "USDA NRCS \u00b7 serves Flagler; Volusia",
   "Phone: (386) 985-4037 ext. 3"
  ]
 }
];
