# RadheEx Reverse-Engineered Network & API Specification

**Generated**: 2026-11-04 01:13:22
**Total Requests Captured**: 206
**Unique API/Data Endpoints**: 86
**WebSocket Messages Logged**: 599

## 1. Discovered API Endpoints & Data Contracts

### `GET /casino/games/launch/EzugiLDLobby.201`
- **Full URL**: `https://api.clubcasinoz.com/casino/games/launch/EzugiLDLobby.201`
- **Status**: `200`
- **Content-Type**: `application/json; charset=utf-8`
- **Saved Payload**: [`GET_api.clubcasinoz.com__casino_games_launch_EzugiLDLobby.201.json`](./responses/GET_api.clubcasinoz.com__casino_games_launch_EzugiLDLobby.201.json)

```json
{
  "url": "https://play.livetables.io//auth/?operatorId=11039019&token=93e93f7a-8dc0-4679-9e01-0442403d3add&language=EN",
  "target": "_self"
}
```

### `GET /delaymarkets/markets/current`
- **Full URL**: `https://api.radheex.com/delaymarkets/markets/current`
- **Status**: `200`
- **Content-Type**: `application/json; charset=utf-8`
- **Saved Payload**: [`GET_api.radheex.com__delaymarkets_markets_current.json`](./responses/GET_api.radheex.com__delaymarkets_markets_current.json)

```json
[
  {
    "eventType": {
      "id": "1",
      "name": "Soccer"
    },
    "competition": {
      "id": "228",
      "name": "UEFA Champions League",
      "provider": "BETFAIR"
    },
    "event": {
      "id": "36223272",
      "name": "Galatasaray v Stuttgart",
      "countryCode": "",
      "venue": "",
      "openDate": "2026-11-03T17:45:00Z"
    },
    "catalogue": {
      "marketId": "1.264321240",
      "marketTime": "2026-11-03T17:45:00Z",
      "marketType": "MATCH_ODDS",
      "bettingType": "ODDS",
      "marketName": "Match Odds",
      "provider": "BETFAIR",
      "marketCondition": {
        "marketId": "1.264321240",
        "betLock": false,
        "minBet": 100,
        "maxBet": 200000,
        "maxProfit": 2000000,
        "betDelay": 8,
        "mtp": 21,
        "al
```

### `GET /manage/Profile/userrebatebonus`
- **Full URL**: `https://api.radheex.com/manage/Profile/userrebatebonus`
- **Status**: `200`
- **Content-Type**: `application/json; charset=utf-8`
- **Saved Payload**: [`GET_api.radheex.com__manage_Profile_userrebatebonus.json`](./responses/GET_api.radheex.com__manage_Profile_userrebatebonus.json)

```json
{
  "operatorId": null,
  "username": null,
  "userId": ":",
  "sportRebateBonus": null
}
```

### `GET /manage/profile`
- **Full URL**: `https://api.radheex.com/manage/profile`
- **Status**: `200`
- **Content-Type**: `application/json; charset=utf-8`
- **Saved Payload**: [`GET_api.radheex.com__manage_profile.json`](./responses/GET_api.radheex.com__manage_profile.json)

```json
{
  "name": null,
  "password": null,
  "email": null,
  "mobile": null,
  "whatsappMobile": null,
  "city": null,
  "remarks": null,
  "referenceName": null,
  "role": "DemoClient",
  "level": 1,
  "parentId": "operator",
  "creditRef": 0,
  "balance": 2000,
  "availableBalance": 2000,
  "upLineBalance": 0,
  "downLineBalance": 0,
  "pnl": 0,
  "deposit": 0,
  "exposure": 0,
  "potentialProfit": 0,
  "commissionDetail": {
    "sportMarkets": 0,
    "otherMarkets": 0,
    "casino": 0,
    "repay": 0
  },
  "sharingDetail": {
    "sports": 0,
    "others": 0,
    "casino": 0
  },
  "minBet": null,
  "maxBet": null,
  "maxProfit": null,
  "betDelay": 0,
  "betLock": false,
  "passwordChangeRequired": false,
  "autoWithdraw": null,
  "blockBonus": null,
  "enablePg": null,
  "enableXorope": n
```

### `GET /marketprovider/Markets/menu`
- **Full URL**: `https://api.radheex.com/marketprovider/Markets/menu`
- **Status**: `200`
- **Content-Type**: `application/json; charset=utf-8`
- **Saved Payload**: [`GET_api.radheex.com__marketprovider_Markets_menu.json`](./responses/GET_api.radheex.com__marketprovider_Markets_menu.json)

```json
[
  {
    "eventTypeId": "4",
    "eventTypeName": "Cricket",
    "competitionId": "10529093",
    "competitionName": "WBBL",
    "eventid": "28045743",
    "eventname": "WBBL",
    "openDate": "2024-12-01T07:10:00Z",
    "marketId": "1.263737530",
    "status": "OPEN",
    "inPlay": false
  },
  {
    "eventTypeId": "1",
    "eventTypeName": "Soccer",
    "competitionId": "228",
    "competitionName": "UEFA Champions League",
    "eventid": "36220990",
    "eventname": "AEK Athens v Real Madrid",
    "openDate": "2026-11-04T17:45:00Z",
    "marketId": "1.264291008",
    "status": "OPEN",
    "inPlay": false
  },
  {
    "eventTypeId": "1",
    "eventTypeName": "Soccer",
    "competitionId": "228",
    "competitionName": "UEFA Champions League",
    "eventid": "36220974",
    "eventname": 
```

### `GET /marketprovider/events/detail/36262637`
- **Full URL**: `https://api.radheex.com/marketprovider/events/detail/36262637`
- **Status**: `200`
- **Content-Type**: `application/json; charset=utf-8`
- **Saved Payload**: [`GET_api.radheex.com__marketprovider_events_detail_36262637.json`](./responses/GET_api.radheex.com__marketprovider_events_detail_36262637.json)

```json
{
  "eventType": {
    "id": "2",
    "name": "Tennis"
  },
  "competition": {
    "id": "12842155",
    "name": "WTA Chennai 2026",
    "provider": "BETFAIR"
  },
  "event": {
    "id": "36262637",
    "name": "Sa Yamalapalli v Sim Waltert",
    "countryCode": null,
    "venue": null,
    "openDate": "2026-11-03T12:30:00Z"
  },
  "catalogues": [
    {
      "marketId": "1.264842870",
      "marketTime": "2026-11-02T03:00:00Z",
      "marketType": "MATCH_ODDS",
      "bettingType": "ODDS",
      "marketName": "Match Odds",
      "provider": "BETFAIR",
      "marketCondition": {
        "marketId": "1.264842870",
        "betLock": false,
        "minBet": 100,
        "maxBet": 10000,
        "maxProfit": 100000,
        "betDelay": 10,
        "mtp": 10,
        "allowUnmatchBet": false,

```

### `GET /marketprovider/markets/current`
- **Full URL**: `https://api.radheex.com/marketprovider/markets/current`
- **Status**: `200`
- **Content-Type**: `application/json; charset=utf-8`
- **Saved Payload**: [`GET_api.radheex.com__marketprovider_markets_current.json`](./responses/GET_api.radheex.com__marketprovider_markets_current.json)

```json
[
  {
    "eventType": {
      "id": "1",
      "name": "Soccer"
    },
    "competition": {
      "id": "7129730",
      "name": "English Championship",
      "provider": "BETFAIR"
    },
    "event": {
      "id": "36253455",
      "name": "Blackburn v Stoke",
      "countryCode": "GB",
      "venue": "",
      "openDate": "2026-11-03T19:45:00Z"
    },
    "catalogue": {
      "marketId": "1.264742339",
      "marketTime": "2026-11-03T19:45:00Z",
      "marketType": "MATCH_ODDS",
      "bettingType": "ODDS",
      "marketName": "Match Odds",
      "provider": "BETFAIR",
      "marketCondition": {
        "marketId": "1.264742339",
        "betLock": false,
        "minBet": 100,
        "maxBet": 100000,
        "maxProfit": 1000000,
        "betDelay": 8,
        "mtp": 21,
        "all
```

### `GET /marketprovider/markets/eventtype/1`
- **Full URL**: `https://api.radheex.com/marketprovider/markets/eventtype/1`
- **Status**: `200`
- **Content-Type**: `application/json; charset=utf-8`
- **Saved Payload**: [`GET_api.radheex.com__marketprovider_markets_eventtype_1.json`](./responses/GET_api.radheex.com__marketprovider_markets_eventtype_1.json)

```json
[
  {
    "eventType": {
      "id": "1",
      "name": "Soccer"
    },
    "competition": {
      "id": "7129730",
      "name": "English Championship",
      "provider": "BETFAIR"
    },
    "event": {
      "id": "36253455",
      "name": "Blackburn v Stoke",
      "countryCode": "GB",
      "venue": "",
      "openDate": "2026-11-03T19:45:00Z"
    },
    "catalogue": {
      "marketId": "1.264742339",
      "marketTime": "2026-11-03T19:45:00Z",
      "marketType": "MATCH_ODDS",
      "bettingType": "ODDS",
      "marketName": "Match Odds",
      "provider": "BETFAIR",
      "marketCondition": {
        "marketId": "1.264742339",
        "betLock": false,
        "minBet": 100,
        "maxBet": 100000,
        "maxProfit": 1000000,
        "betDelay": 8,
        "mtp": 21,
        "all
```

### `GET /marketprovider/markets/eventtype/2`
- **Full URL**: `https://api.radheex.com/marketprovider/markets/eventtype/2`
- **Status**: `200`
- **Content-Type**: `application/json; charset=utf-8`
- **Saved Payload**: [`GET_api.radheex.com__marketprovider_markets_eventtype_2.json`](./responses/GET_api.radheex.com__marketprovider_markets_eventtype_2.json)

```json
[
  {
    "eventType": {
      "id": "2",
      "name": "Tennis"
    },
    "competition": {
      "id": "12842240",
      "name": "ATP Paris 2026",
      "provider": "BETFAIR"
    },
    "event": {
      "id": "36263401",
      "name": "Struff v Ar Gea",
      "countryCode": "",
      "venue": "",
      "openDate": "2026-11-03T17:15:00Z"
    },
    "catalogue": {
      "marketId": "1.264845945",
      "marketTime": "2026-11-01T10:00:00Z",
      "marketType": "MATCH_ODDS",
      "bettingType": "ODDS",
      "marketName": "Match Odds",
      "provider": "BETFAIR",
      "marketCondition": {
        "marketId": "1.264845945",
        "betLock": false,
        "minBet": 100,
        "maxBet": 10000,
        "maxProfit": 100000,
        "betDelay": 10,
        "mtp": 10,
        "allowUnmatchB
```

### `GET /marketprovider/markets/eventtype/4`
- **Full URL**: `https://api.radheex.com/marketprovider/markets/eventtype/4`
- **Status**: `200`
- **Content-Type**: `application/json; charset=utf-8`
- **Saved Payload**: [`GET_api.radheex.com__marketprovider_markets_eventtype_4.json`](./responses/GET_api.radheex.com__marketprovider_markets_eventtype_4.json)

```json
[
  {
    "eventType": {
      "id": "4",
      "name": "Cricket"
    },
    "competition": {
      "id": "10529093",
      "name": "WBBL",
      "provider": "BETFAIR"
    },
    "event": {
      "id": "28045743",
      "name": "WBBL",
      "countryCode": "AU",
      "venue": "",
      "openDate": "2024-12-01T07:10:00Z"
    },
    "catalogue": {
      "marketId": "43907183",
      "marketTime": "2024-12-01T07:10:00Z",
      "marketType": "BOOKMAKER",
      "bettingType": "BOOKMAKER",
      "marketName": "WBBL 2026 Winner Cup Bookmaker",
      "provider": "BETHUBS",
      "marketCondition": {
        "marketId": "43907183",
        "betLock": false,
        "minBet": 100,
        "maxBet": 25000,
        "maxProfit": 500000,
        "betDelay": 0,
        "mtp": 4,
        "allowUnmatchBet
```

### `GET /marketprovider/markets/live`
- **Full URL**: `https://api.radheex.com/marketprovider/markets/live`
- **Status**: `200`
- **Content-Type**: `application/json; charset=utf-8`
- **Saved Payload**: [`GET_api.radheex.com__marketprovider_markets_live.json`](./responses/GET_api.radheex.com__marketprovider_markets_live.json)

```json
[
  {
    "eventType": {
      "id": "2",
      "name": "Tennis"
    },
    "competition": {
      "id": "12842155",
      "name": "WTA Chennai 2026",
      "provider": "BETFAIR"
    },
    "event": {
      "id": "36262637",
      "name": "Sa Yamalapalli v Sim Waltert",
      "countryCode": "",
      "venue": "",
      "openDate": "2026-11-03T12:30:00Z"
    },
    "catalogue": {
      "marketId": "1.264842870",
      "marketTime": "2026-11-02T03:00:00Z",
      "marketType": "MATCH_ODDS",
      "bettingType": "ODDS",
      "marketName": "Match Odds",
      "provider": "BETFAIR",
      "marketCondition": {
        "marketId": "1.264842870",
        "betLock": false,
        "minBet": 100,
        "maxBet": 10000,
        "maxProfit": 100000,
        "betDelay": 10,
        "mtp": 10,
       
```

### `GET /marketprovider/marquee`
- **Full URL**: `https://api.radheex.com/marketprovider/marquee`
- **Status**: `200`
- **Content-Type**: `application/json; charset=utf-8`
- **Saved Payload**: [`GET_api.radheex.com__marketprovider_marquee.json`](./responses/GET_api.radheex.com__marketprovider_marquee.json)

```json
{
  "message": " 1\ufe0f\u20e3Welcome To Our Exchange .....\u2728\u2728 2\ufe0f\u20e3WBBL 2026  ..Winner Cup Bets Started In Our Exchange.......\u2728\u2728\u2728\n\n\n"
}
```

### `GET /sso/auth/requestcaptcha`
- **Full URL**: `https://api.radheex.com/sso/auth/requestcaptcha`
- **Status**: `200`
- **Content-Type**: `application/json; charset=utf-8`
- **Saved Payload**: [`GET_api.radheex.com__sso_auth_requestcaptcha.json`](./responses/GET_api.radheex.com__sso_auth_requestcaptcha.json)

```json
{
  "requestId": "9d6f583c-aeec-4237-b0f3-1edc22f559c9",
  "captchaImage": "iVBORw0KGgoAAAANSUhEUgAAAHgAAAAeEAYAAAC3WQbWAAAAIGNIUk0AAHomAACAhAAA+gAAAIDoAAB1MAAA6mAAADqYAAAXcJy6UTwAAAAGYktHRP///////wlY99wAAAAHdElNRQfqCwMTKg6I3fC9AAAfg0lEQVR42q1de3SV1ZUPCU8JgYZAFMIzxICpg9gRSjUKKF4JCl5sq9KMOq1ekUgFBxhMrY7a2sFXQB3t0FLGuQpV7LQlopeHYiOKmK9YEGNHxHq7fBQCuJC5PAS654/tz9/e57tZs9as3rXgJvee75x99vt1TgoyyXSbiIhIrkVEJIokeOnn2USuJdciov+LiPBJfWUTmaSISLK9qV5n0nc/D186ujGLb7FONqHP+dlFRPTzbEJnT7dFkc6abhNpqtcZoiiKFE6/amNWv88kdYdRlGznbICGz2SS+p3Oab/3M+O3jvCGuXItOl+yXfdldwcYAHc2odi0MNn18bO+6/+6awtHNtGYFWnMcr3GrIif1a4fRbrPXEu4F/1d5yMkOlMmiX1GEfYBvGFPTfVK1zimdSzmxzdYX/GBT/G8fg+6WEyDZgoX10i3EbfgM+wyk8QnUaTjQBm7G88H+KapPo5PSgVGpdv0J+XepnrgkThKt/nVMknuze+R9FScihR0JFhN9UScR2Eq5RmajBUKtDJMFOnY2rm6hVTKjkql0m3KtJkkSeTJFUU6
```

### `GET /css2`
- **Full URL**: `https://fonts.googleapis.com/css2?family=Poppins:wght@200;300;400;500;600;700&display=swap`
- **Status**: `200`
- **Content-Type**: `text/css; charset=utf-8`
- **Saved Payload**: [`GET_fonts.googleapis.com__css2.txt`](./responses/GET_fonts.googleapis.com__css2.txt)

```json
/* devanagari */
@font-face {
  font-family: 'Poppins';
  font-style: normal;
  font-weight: 200;
  font-display: swap;
  src: url(https://fonts.gstatic.com/s/poppins/v24/pxiByp8kv8JHgFVrLFj_Z11lFc-K.woff2) format('woff2');
  unicode-range: U+0900-097F, U+1CD0-1CF4, U+1CF7-1CF9, U+200C-200D, U+20A8, U+20B9, U+20F0, U+25CC, U+A830-A839, U+A8E0-A8FF, U+11B00-11B0A;
}
/* latin-ext */
@font-face {
  font-family: 'Poppins';
  font-style: normal;
  font-weight: 200;
  font-display: swap;
  src: url(ht
```

### `GET /css2`
- **Full URL**: `https://fonts.googleapis.com/css2?family=Roboto+Condensed:wght@300;400;700&display=swap`
- **Status**: `200`
- **Content-Type**: `text/css; charset=utf-8`
- **Saved Payload**: [`GET_fonts.googleapis.com__css2.txt`](./responses/GET_fonts.googleapis.com__css2.txt)

```json
/* cyrillic-ext */
@font-face {
  font-family: 'Roboto Condensed';
  font-style: normal;
  font-weight: 300;
  font-display: swap;
  src: url(https://fonts.gstatic.com/s/robotocondensed/v31/ieVl2ZhZI2eCN5jzbjEETS9weq8-19-7DRs5.woff2) format('woff2');
  unicode-range: U+0460-052F, U+1C80-1C8A, U+20B4, U+2DE0-2DFF, U+A640-A69F, U+FE2E-FE2F;
}
/* cyrillic */
@font-face {
  font-family: 'Roboto Condensed';
  font-style: normal;
  font-weight: 300;
  font-display: swap;
  src: url(https://fonts.gstat
```

### `GET /css`
- **Full URL**: `https://fonts.googleapis.com/css?family=Roboto:300,400,500,700,900&subset=latin,latin-ext`
- **Status**: `200`
- **Content-Type**: `text/css; charset=utf-8`
- **Saved Payload**: [`GET_fonts.googleapis.com__css.txt`](./responses/GET_fonts.googleapis.com__css.txt)

```json
/* cyrillic-ext */
@font-face {
  font-family: 'Roboto';
  font-style: normal;
  font-weight: 300;
  font-stretch: 100%;
  src: url(https://fonts.gstatic.com/s/roboto/v51/KFO7CnqEu92Fr1ME7kSn66aGLdTylUAMa3GUBGEe.woff2) format('woff2');
  unicode-range: U+0460-052F, U+1C80-1C8A, U+20B4, U+2DE0-2DFF, U+A640-A69F, U+FE2E-FE2F;
}
/* cyrillic */
@font-face {
  font-family: 'Roboto';
  font-style: normal;
  font-weight: 300;
  font-stretch: 100%;
  src: url(https://fonts.gstatic.com/s/roboto/v51/KFO7C
```

### `GET /banners/desktop_banner_1.jpg`
- **Full URL**: `https://images.staticcontents.net/banners/desktop_banner_1.jpg`
- **Status**: `200`
- **Content-Type**: `image/jpeg`
- **Saved Payload**: [`GET_images.staticcontents.net__banners_desktop_banner_1.jpg.txt`](./responses/GET_images.staticcontents.net__banners_desktop_banner_1.jpg.txt)

```json
  


		

)))))//////////
		

    ((&((//////////  x Adobe d    , "                             !1"AQ2aqBR#r3Vb$CSTst45DUcd%EFu&6'e  	   !1AQ"Raq2#B3brCS4$%5c    ? Ѿӄν-?AԶVHOj"d¼NڙzL(wlR|**Ƹw?:;GN hRH~tg<(lRSY(~tw?:n.t ZvGC{BGK{ҡ$ΖG@
T!;{iPvGK{V,.DcU@,OJI7?:8nI$Q1:ݳ4iZ]ppytr282
.N
(J?/SdXdL/o
```

### `GET /banners/desktop_banner_12.jpg`
- **Full URL**: `https://images.staticcontents.net/banners/desktop_banner_12.jpg`
- **Status**: `200`
- **Content-Type**: `image/jpeg`
- **Saved Payload**: [`GET_images.staticcontents.net__banners_desktop_banner_12.jpg.txt`](./responses/GET_images.staticcontents.net__banners_desktop_banner_12.jpg.txt)

```json
XICC_PROFILE   HLino  mntrRGB XYZ   	  1  acspMSFT    IEC sRGB                  -HP                                                 cprt  P   3desc     lwtpt     bkpt     rXYZ     gXYZ  ,   bXYZ  @   dmnd  T   pdmdd     vued  L   view     $lumi     meas     $tech  0   rTRC  <  gTRC  <  bTRC  <  text    Copyright (c) 1998 Hewlett-Packard Company  desc       sRGB IEC61966-2.1           sRGB IEC61966-2.1                                                 
```

### `GET /banners/desktop_banner_13.jpg`
- **Full URL**: `https://images.staticcontents.net/banners/desktop_banner_13.jpg`
- **Status**: `200`
- **Content-Type**: `image/jpeg`
- **Saved Payload**: [`GET_images.staticcontents.net__banners_desktop_banner_13.jpg.txt`](./responses/GET_images.staticcontents.net__banners_desktop_banner_13.jpg.txt)

```json
XICC_PROFILE   HLino  mntrRGB XYZ   	  1  acspMSFT    IEC sRGB                  -HP                                                 cprt  P   3desc     lwtpt     bkpt     rXYZ     gXYZ  ,   bXYZ  @   dmnd  T   pdmdd     vued  L   view     $lumi     meas     $tech  0   rTRC  <  gTRC  <  bTRC  <  text    Copyright (c) 1998 Hewlett-Packard Company  desc       sRGB IEC61966-2.1           sRGB IEC61966-2.1                                                 
```

### `GET /banners/desktop_banner_14.jpg`
- **Full URL**: `https://images.staticcontents.net/banners/desktop_banner_14.jpg`
- **Status**: `200`
- **Content-Type**: `image/jpeg`
- **Saved Payload**: [`GET_images.staticcontents.net__banners_desktop_banner_14.jpg.txt`](./responses/GET_images.staticcontents.net__banners_desktop_banner_14.jpg.txt)

```json
XICC_PROFILE   HLino  mntrRGB XYZ   	  1  acspMSFT    IEC sRGB                  -HP                                                 cprt  P   3desc     lwtpt     bkpt     rXYZ     gXYZ  ,   bXYZ  @   dmnd  T   pdmdd     vued  L   view     $lumi     meas     $tech  0   rTRC  <  gTRC  <  bTRC  <  text    Copyright (c) 1998 Hewlett-Packard Company  desc       sRGB IEC61966-2.1           sRGB IEC61966-2.1                                                 
```

### `GET /banners/desktop_banner_15.jpg`
- **Full URL**: `https://images.staticcontents.net/banners/desktop_banner_15.jpg`
- **Status**: `200`
- **Content-Type**: `image/jpeg`
- **Saved Payload**: [`GET_images.staticcontents.net__banners_desktop_banner_15.jpg.txt`](./responses/GET_images.staticcontents.net__banners_desktop_banner_15.jpg.txt)

```json
XICC_PROFILE   HLino  mntrRGB XYZ   	  1  acspMSFT    IEC sRGB                  -HP                                                 cprt  P   3desc     lwtpt     bkpt     rXYZ     gXYZ  ,   bXYZ  @   dmnd  T   pdmdd     vued  L   view     $lumi     meas     $tech  0   rTRC  <  gTRC  <  bTRC  <  text    Copyright (c) 1998 Hewlett-Packard Company  desc       sRGB IEC61966-2.1           sRGB IEC61966-2.1                                                 
```

### `GET /banners/desktop_banner_16.jpg`
- **Full URL**: `https://images.staticcontents.net/banners/desktop_banner_16.jpg`
- **Status**: `200`
- **Content-Type**: `image/jpeg`
- **Saved Payload**: [`GET_images.staticcontents.net__banners_desktop_banner_16.jpg.txt`](./responses/GET_images.staticcontents.net__banners_desktop_banner_16.jpg.txt)

```json
XICC_PROFILE   HLino  mntrRGB XYZ   	  1  acspMSFT    IEC sRGB                  -HP                                                 cprt  P   3desc     lwtpt     bkpt     rXYZ     gXYZ  ,   bXYZ  @   dmnd  T   pdmdd     vued  L   view     $lumi     meas     $tech  0   rTRC  <  gTRC  <  bTRC  <  text    Copyright (c) 1998 Hewlett-Packard Company  desc       sRGB IEC61966-2.1           sRGB IEC61966-2.1                                                 
```

### `GET /banners/list.json`
- **Full URL**: `https://images.staticcontents.net/banners/list.json`
- **Status**: `200`
- **Content-Type**: `text/json`
- **Saved Payload**: [`GET_images.staticcontents.net__banners_list.json.json`](./responses/GET_images.staticcontents.net__banners_list.json.json)

```json
{
  "desktop": [
    "1.jpg",
    "12.jpg",
    "13.jpg",
    "14.jpg",
    "15.jpg",
    "16.jpg",
    "6.jpg"
  ],
  "mobile": [
    "1.jpg",
    "12.jpg",
    "13.jpg",
    "14.jpg",
    "15.jpg",
    "16.jpg",
    "6.jpg"
  ]
}
```

### `GET /banners/mobile_banner_1.jpg`
- **Full URL**: `https://images.staticcontents.net/banners/mobile_banner_1.jpg`
- **Status**: `200`
- **Content-Type**: `image/jpeg`
- **Saved Payload**: [`GET_images.staticcontents.net__banners_mobile_banner_1.jpg.txt`](./responses/GET_images.staticcontents.net__banners_mobile_banner_1.jpg.txt)

```json
  




	
  ` Adobe d    ,                  	             	 !1"AQ2aq#BR$3br	%4CcDESdstu56FTUef&Vv  		 !1AQ"a2qBR#br3CScs$4Tdt    ? l''\cAl)B8N2{)4ͺA_Ҏu%?2܈  9njSo56Wv'-kc)VF:c}KMAZiFEI*CJTJPmg̦u$B)'^"EI%IN
I{I/S'$~ՇOSވS,&,`3@mYڠx9Lnu2;m#8!*PV:~zMi˅$;
```

### `GET /banners/mobile_banner_12.jpg`
- **Full URL**: `https://images.staticcontents.net/banners/mobile_banner_12.jpg`
- **Status**: `200`
- **Content-Type**: `image/jpeg`
- **Saved Payload**: [`GET_images.staticcontents.net__banners_mobile_banner_12.jpg.txt`](./responses/GET_images.staticcontents.net__banners_mobile_banner_12.jpg.txt)

```json
XICC_PROFILE   HLino  mntrRGB XYZ   	  1  acspMSFT    IEC sRGB                  -HP                                                 cprt  P   3desc     lwtpt     bkpt     rXYZ     gXYZ  ,   bXYZ  @   dmnd  T   pdmdd     vued  L   view     $lumi     meas     $tech  0   rTRC  <  gTRC  <  bTRC  <  text    Copyright (c) 1998 Hewlett-Packard Company  desc       sRGB IEC61966-2.1           sRGB IEC61966-2.1                                                 
```

### `GET /banners/mobile_banner_13.jpg`
- **Full URL**: `https://images.staticcontents.net/banners/mobile_banner_13.jpg`
- **Status**: `200`
- **Content-Type**: `image/jpeg`
- **Saved Payload**: [`GET_images.staticcontents.net__banners_mobile_banner_13.jpg.txt`](./responses/GET_images.staticcontents.net__banners_mobile_banner_13.jpg.txt)

```json
XICC_PROFILE   HLino  mntrRGB XYZ   	  1  acspMSFT    IEC sRGB                  -HP                                                 cprt  P   3desc     lwtpt     bkpt     rXYZ     gXYZ  ,   bXYZ  @   dmnd  T   pdmdd     vued  L   view     $lumi     meas     $tech  0   rTRC  <  gTRC  <  bTRC  <  text    Copyright (c) 1998 Hewlett-Packard Company  desc       sRGB IEC61966-2.1           sRGB IEC61966-2.1                                                 
```

### `GET /banners/mobile_banner_14.jpg`
- **Full URL**: `https://images.staticcontents.net/banners/mobile_banner_14.jpg`
- **Status**: `200`
- **Content-Type**: `image/jpeg`
- **Saved Payload**: [`GET_images.staticcontents.net__banners_mobile_banner_14.jpg.txt`](./responses/GET_images.staticcontents.net__banners_mobile_banner_14.jpg.txt)

```json
XICC_PROFILE   HLino  mntrRGB XYZ   	  1  acspMSFT    IEC sRGB                  -HP                                                 cprt  P   3desc     lwtpt     bkpt     rXYZ     gXYZ  ,   bXYZ  @   dmnd  T   pdmdd     vued  L   view     $lumi     meas     $tech  0   rTRC  <  gTRC  <  bTRC  <  text    Copyright (c) 1998 Hewlett-Packard Company  desc       sRGB IEC61966-2.1           sRGB IEC61966-2.1                                                 
```

### `GET /banners/mobile_banner_15.jpg`
- **Full URL**: `https://images.staticcontents.net/banners/mobile_banner_15.jpg`
- **Status**: `200`
- **Content-Type**: `image/jpeg`
- **Saved Payload**: [`GET_images.staticcontents.net__banners_mobile_banner_15.jpg.txt`](./responses/GET_images.staticcontents.net__banners_mobile_banner_15.jpg.txt)

```json
XICC_PROFILE   HLino  mntrRGB XYZ   	  1  acspMSFT    IEC sRGB                  -HP                                                 cprt  P   3desc     lwtpt     bkpt     rXYZ     gXYZ  ,   bXYZ  @   dmnd  T   pdmdd     vued  L   view     $lumi     meas     $tech  0   rTRC  <  gTRC  <  bTRC  <  text    Copyright (c) 1998 Hewlett-Packard Company  desc       sRGB IEC61966-2.1           sRGB IEC61966-2.1                                                 
```

### `GET /banners/mobile_banner_16.jpg`
- **Full URL**: `https://images.staticcontents.net/banners/mobile_banner_16.jpg`
- **Status**: `200`
- **Content-Type**: `image/jpeg`
- **Saved Payload**: [`GET_images.staticcontents.net__banners_mobile_banner_16.jpg.txt`](./responses/GET_images.staticcontents.net__banners_mobile_banner_16.jpg.txt)

```json
XICC_PROFILE   HLino  mntrRGB XYZ   	  1  acspMSFT    IEC sRGB                  -HP                                                 cprt  P   3desc     lwtpt     bkpt     rXYZ     gXYZ  ,   bXYZ  @   dmnd  T   pdmdd     vued  L   view     $lumi     meas     $tech  0   rTRC  <  gTRC  <  bTRC  <  text    Copyright (c) 1998 Hewlett-Packard Company  desc       sRGB IEC61966-2.1           sRGB IEC61966-2.1                                                 
```

### `GET /casino/banner/Cricket-banner.jpg`
- **Full URL**: `https://images.staticcontents.net/casino/banner/Cricket-banner.jpg`
- **Status**: `200`
- **Content-Type**: `image/jpeg`
- **Saved Payload**: [`GET_images.staticcontents.net__casino_banner_Cricket-banner.jpg.txt`](./responses/GET_images.staticcontents.net__casino_banner_Cricket-banner.jpg.txt)

```json
  					&&&&&++++++++++		
	

$$#$$++++++++++  x Adobe d    , "                             !1AQa"q2#BR3brCS$%4cDs5TEU   !1AQ"aq2R#BSr3CbTc$4s    ? @WjF*=SI" N֫r`._n@$L|IU;ʻ'W1h 5+/V45YMco*f$ +>iZH?*ʔ;m<Ĺ]!A<}(o<GH;R@߈13T0A3jr_V:G^WM,*` ,o1Q:D|$H}SPdA:>#m@LR1_w;ҡ{;p!#MUZp1QcΦojc(
```

### `GET /casino/banner/Soccer-banner.jpg`
- **Full URL**: `https://images.staticcontents.net/casino/banner/Soccer-banner.jpg`
- **Status**: `200`
- **Content-Type**: `image/jpeg`
- **Saved Payload**: [`GET_images.staticcontents.net__casino_banner_Soccer-banner.jpg.txt`](./responses/GET_images.staticcontents.net__casino_banner_Soccer-banner.jpg.txt)

```json
  

		"""""""""""""""""""""""""""""""""""""""""""""""""""""""""""   Adobe d    ,                	              !1"AQa2q#BRSUbr3V$7CT46cstu%5EDd'(FW  !1AQ"a2BRq#b$3rCS    ? .8H     @ZOԕ,LySn3]y4,mhewĭB>8FgYK49NRNR)dnO5$)dc1tH؄lMe5Fm4ohQꬪ.׫hyoUQN{`=	VkULrɚ2-kgTR)ccE;tVԴdݠI^hZ~ѕfKBR+d8P A(L8ͤfقx
```

### `GET /casino/banner/Tennis-banner.jpg`
- **Full URL**: `https://images.staticcontents.net/casino/banner/Tennis-banner.jpg`
- **Status**: `200`
- **Content-Type**: `image/jpeg`
- **Saved Payload**: [`GET_images.staticcontents.net__casino_banner_Tennis-banner.jpg.txt`](./responses/GET_images.staticcontents.net__casino_banner_Tennis-banner.jpg.txt)

```json
  

		"""""""""""""""""""""""""""""""""""""""""""""""""""""""""""   Adobe d    ,                 	             	  !1AQ"2aqR#Bbr3U$c4CDESTs%Äd&5t   !1"AQ2aq#B3Rbr$4C    ? r'ʶN,~5X |nCuHXQLd>`9e|)ڶ+AC^άjEHWDɐ]^I/T
 :H$*
HA =*"d҅#@LP˯ՠ!^m  `'ʕhZ#E"Nu*(g)TQ4!8'2桲P%0p*ё"%qВvnQ`tT-XQ  AA C rM
```

### `GET /casino/banner/images/Account-Statement.svg`
- **Full URL**: `https://images.staticcontents.net/casino/banner/images/Account-Statement.svg`
- **Status**: `200`
- **Content-Type**: `image/svg+xml`
- **Saved Payload**: [`GET_images.staticcontents.net__casino_banner_images_Account-Statement.svg.txt`](./responses/GET_images.staticcontents.net__casino_banner_images_Account-Statement.svg.txt)

```json
<svg id="Layer_5" enable-background="new 0 0 64 64" height="512" viewBox="0 0 64 64" width="512" xmlns="http://www.w3.org/2000/svg"><g><g><g><path d="m54 4v18l-.01.04c-.16-.03-.32-.04-.48-.04h-.11c-.9 0-1.76.35-2.41.97l-2.56 2.46-5.79 5.57h-4.36c-1.19 0-2.34.35-3.31 1h-8.97-8-8v6 20h8 8 8 8 8v-11.28-.01l4-1.14v14.43c0 1.1-.9 2-2 2h-44c-1.1 0-2-.9-2-2v-40c1.67 1.25 3.75 2 6 2 5.52 0 10-4.48 10-10s-4.48-10-10-10h40c1.1 0 2 .9 2 2z" fill="#e6e9ed"/></g><g><path d="m10 32h8v6h-8z" fill="#ff826e"/></
```

### `GET /casino/banner/images/aviator-icon.svg`
- **Full URL**: `https://images.staticcontents.net/casino/banner/images/aviator-icon.svg`
- **Status**: `200`
- **Content-Type**: `image/svg+xml`
- **Saved Payload**: [`GET_images.staticcontents.net__casino_banner_images_aviator-icon.svg.txt`](./responses/GET_images.staticcontents.net__casino_banner_images_aviator-icon.svg.txt)

```json
<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE svg PUBLIC "-//W3C//DTD SVG 1.1//EN" "http://www.w3.org/Graphics/SVG/1.1/DTD/svg11.dtd">
<!-- Creator: CorelDRAW X7 -->
<svg xmlns="http://www.w3.org/2000/svg" xml:space="preserve" width="43.3492mm" height="22.8598mm" version="1.1" style="shape-rendering:geometricPrecision; text-rendering:geometricPrecision; image-rendering:optimizeQuality; fill-rule:evenodd; clip-rule:evenodd"
viewBox="0 0 4335 2286"
 xmlns:xlink="http://www.w3.org/1999/xlin
```

### `GET /casino/banner/images/bet-history.svg`
- **Full URL**: `https://images.staticcontents.net/casino/banner/images/bet-history.svg`
- **Status**: `200`
- **Content-Type**: `image/svg+xml`
- **Saved Payload**: [`GET_images.staticcontents.net__casino_banner_images_bet-history.svg.txt`](./responses/GET_images.staticcontents.net__casino_banner_images_bet-history.svg.txt)

```json
<svg id="Capa_1" enable-background="new 0 0 512 512" height="512" viewBox="0 0 512 512" width="512" xmlns="http://www.w3.org/2000/svg"><g><g><path d="m367.876 46.853c0-21.686 17.58-39.266 39.266-39.266h-305.632c-17.246 0-31.226 13.98-31.226 31.226v355.585h297.592v-288.279z" fill="#ffe07d"/></g><path d="m383.436 7.586c-21.686 0-39.266 17.58-39.266 39.266v39.266 20 96.449c0 9.162-6.018 17.312-14.835 19.799-65.025 18.335-112.685 78.087-112.685 148.978 0 18.637 3.296 36.504 9.333 53.053h118.187 23.7
```

### `GET /casino/banner/images/change-password.svg`
- **Full URL**: `https://images.staticcontents.net/casino/banner/images/change-password.svg`
- **Status**: `200`
- **Content-Type**: `image/svg+xml`
- **Saved Payload**: [`GET_images.staticcontents.net__casino_banner_images_change-password.svg.txt`](./responses/GET_images.staticcontents.net__casino_banner_images_change-password.svg.txt)

```json
<?xml version="1.0" encoding="iso-8859-1"?>
<!-- Generator: Adobe Illustrator 19.0.0, SVG Export Plug-In . SVG Version: 6.00 Build 0)  -->
<svg version="1.1" id="Capa_1" xmlns="http://www.w3.org/2000/svg" xmlns:xlink="http://www.w3.org/1999/xlink" x="0px" y="0px"
	 viewBox="0 0 512 512" style="enable-background:new 0 0 512 512;" xml:space="preserve">
<path style="fill:#303C42;" d="M437.333,192h-32v-42.667C405.333,66.99,338.344,0,256,0S106.667,66.99,106.667,149.333V192h-32
	C68.771,192,64,19
```

### `GET /casino/banner/images/coin.svg`
- **Full URL**: `https://images.staticcontents.net/casino/banner/images/coin.svg`
- **Status**: `200`
- **Content-Type**: `image/svg+xml`
- **Saved Payload**: [`GET_images.staticcontents.net__casino_banner_images_coin.svg.txt`](./responses/GET_images.staticcontents.net__casino_banner_images_coin.svg.txt)

```json
<?xml version="1.0" encoding="iso-8859-1"?>
<!-- Generator: Adobe Illustrator 19.0.0, SVG Export Plug-In . SVG Version: 6.00 Build 0)  -->
<svg version="1.1" id="Capa_1" xmlns="http://www.w3.org/2000/svg" xmlns:xlink="http://www.w3.org/1999/xlink" x="0px" y="0px"
	 viewBox="0 0 56 56" style="enable-background:new 0 0 56 56;" xml:space="preserve">
<g id="XMLID_100_">
	<path id="XMLID_99_" style="fill:#FFD949;" d="M31,56C17.469,56,6.5,43.464,6.5,28S17.469,0,31,0c13.531,0,24.5,12.536,24.5,28

```

### `GET /casino/banner/images/inout-icon-b.svg`
- **Full URL**: `https://images.staticcontents.net/casino/banner/images/inout-icon-b.svg`
- **Status**: `200`
- **Content-Type**: `image/svg+xml`
- **Saved Payload**: [`GET_images.staticcontents.net__casino_banner_images_inout-icon-b.svg.txt`](./responses/GET_images.staticcontents.net__casino_banner_images_inout-icon-b.svg.txt)

```json
<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE svg PUBLIC "-//W3C//DTD SVG 1.1//EN" "http://www.w3.org/Graphics/SVG/1.1/DTD/svg11.dtd">
<!-- Creator: CorelDRAW -->
<svg xmlns="http://www.w3.org/2000/svg" xml:space="preserve" width="120px" height="100px" version="1.1" style="shape-rendering:geometricPrecision; text-rendering:geometricPrecision; image-rendering:optimizeQuality; fill-rule:evenodd; clip-rule:evenodd"
viewBox="0 0 120 100"
 xmlns:xlink="http://www.w3.org/1999/xlink"
 xmlns:xo
```

### `GET /casino/banner/images/inout-icon.svg`
- **Full URL**: `https://images.staticcontents.net/casino/banner/images/inout-icon.svg`
- **Status**: `200`
- **Content-Type**: `image/svg+xml`
- **Saved Payload**: [`GET_images.staticcontents.net__casino_banner_images_inout-icon.svg.txt`](./responses/GET_images.staticcontents.net__casino_banner_images_inout-icon.svg.txt)

```json
<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE svg PUBLIC "-//W3C//DTD SVG 1.1//EN" "http://www.w3.org/Graphics/SVG/1.1/DTD/svg11.dtd">
<!-- Creator: CorelDRAW -->
<svg xmlns="http://www.w3.org/2000/svg" xml:space="preserve" width="500px" height="155px" version="1.1" style="shape-rendering:geometricPrecision; text-rendering:geometricPrecision; image-rendering:optimizeQuality; fill-rule:evenodd; clip-rule:evenodd"
viewBox="0 0 500 155"
 xmlns:xlink="http://www.w3.org/1999/xlink"
 xmlns:xo
```

### `GET /casino/banner/images/l.gif`
- **Full URL**: `https://images.staticcontents.net/casino/banner/images/l.gif`
- **Status**: `200`
- **Content-Type**: `image/gif`
- **Saved Payload**: [`GET_images.staticcontents.net__casino_banner_images_l.gif.txt`](./responses/GET_images.staticcontents.net__casino_banner_images_l.gif.txt)

```json
GIF89aD I   !NETSCAPE2.0   !	
  ,    D I  ڋ޼Hv-CAS c OcJOw5֒Fo]L4tEEa}|7SҧX')9IYIHyi:**Abi([GKg{k,<L\l|\Y  !	
  ,    D I  ڋ޼H9 
nk[g7[`@hY/hh*TJT(	[.y]1b>nɎoYH'4ׇH)9ٸhxWhyB9h)xgʈZ)+J,<L\l\  !	
  ,    D I  ڋ޼H扦
ʹ.-/~[>0ۍdiIEЊTRRN1uf<RQާ7(reFv)9I!X7EY
Zjtٙ&{F[{Z,<L\l|P  !	
  ,    D I  ڋ޼H扦
ʹ.-/~<&)bɗ@4=(I	ܮQqZ-_uZnWޟ|BسjQ67fefx5'x7U(W)a谹et#jpʓ%;x,<L\Q  !	
  ,    D I  ڋ޼H扦
ʹ.-/~<&)bɗ@4=(I	ܮ섵PE
```

### `GET /casino/banner/images/log-out.svg`
- **Full URL**: `https://images.staticcontents.net/casino/banner/images/log-out.svg`
- **Status**: `200`
- **Content-Type**: `image/svg+xml`
- **Saved Payload**: [`GET_images.staticcontents.net__casino_banner_images_log-out.svg.txt`](./responses/GET_images.staticcontents.net__casino_banner_images_log-out.svg.txt)

```json
<svg height="511pt" viewBox="-15 0 511 511.99988" width="511pt" xmlns="http://www.w3.org/2000/svg"><path d="m330.5 15.007812v422c0 8.398438-6.597656 15-15 15h-120c-8.402344 0-15-6.601562-15-15l-180-422c0-8.402343 6.597656-14.9999995 15-14.9999995h300c8.402344 0 15 6.5976565 15 14.9999995zm0 0" fill="#07485e"/><path d="m330.5 15.007812v422c0 8.398438-6.597656 15-15 15h-120c-8.402344 0-15-6.601562-15-15l-45-105v-331.9999995h180c8.402344 0 15 6.5976565 15 14.9999995zm0 0" fill="#03232e"/><path d="m
```

### `GET /casino/banner/images/profit-loss-report.svg`
- **Full URL**: `https://images.staticcontents.net/casino/banner/images/profit-loss-report.svg`
- **Status**: `200`
- **Content-Type**: `image/svg+xml`
- **Saved Payload**: [`GET_images.staticcontents.net__casino_banner_images_profit-loss-report.svg.txt`](./responses/GET_images.staticcontents.net__casino_banner_images_profit-loss-report.svg.txt)

```json
<svg height="512" viewBox="0 0 64 64" width="512" xmlns="http://www.w3.org/2000/svg"><g id="Analysis-report-document-develop-infromation"><path d="m61 14v45a2.006 2.006 0 0 1 -2 2h-34a2.006 2.006 0 0 1 -2-2v-54a2.006 2.006 0 0 1 2-2h25v9a2.006 2.006 0 0 0 2 2z" fill="#fee9ab"/><path d="m61 14v45a2.006 2.006 0 0 1 -2 2h-4a2.006 2.006 0 0 0 2-2v-45z" fill="#ffd422"/><path d="m61 14h-9a2.006 2.006 0 0 1 -2-2v-9z" fill="#ff7956"/><circle cx="49" cy="49" fill="#bdfdff" r="8"/><path d="m47 28h-20v-20a
```

### `GET /casino/banner/images/rules.svg`
- **Full URL**: `https://images.staticcontents.net/casino/banner/images/rules.svg`
- **Status**: `200`
- **Content-Type**: `image/svg+xml`
- **Saved Payload**: [`GET_images.staticcontents.net__casino_banner_images_rules.svg.txt`](./responses/GET_images.staticcontents.net__casino_banner_images_rules.svg.txt)

```json
<svg height="512" viewBox="0 0 57 59" width="512" xmlns="http://www.w3.org/2000/svg"><g id="Page-1" fill="none" fill-rule="evenodd"><g id="024---Auction" fill-rule="nonzero"><path id="Shape" d="m55 5c0 3 1 4 1 4h-6v-4h-10v4h-20c-2.209139 0-4-1.790861-4-4s1.790861-4 4-4h36s-1 1-1 4z" fill="#f5efca"/><path id="Shape" d="m56 9v38c0 .5522847-.4477153 1-1 1h-34v-3c-.0032948-1.1032019-.8967981-1.9967052-2-2v-12h7v1c0 .5522847.4477153 1 1 1h2c1.6568542 0 3-1.3431458 3-3v-14c0-1.6568542-1.3431458-3-3-3h
```

### `GET /casino/banner/images/set-button-value.svg`
- **Full URL**: `https://images.staticcontents.net/casino/banner/images/set-button-value.svg`
- **Status**: `200`
- **Content-Type**: `image/svg+xml`
- **Saved Payload**: [`GET_images.staticcontents.net__casino_banner_images_set-button-value.svg.txt`](./responses/GET_images.staticcontents.net__casino_banner_images_set-button-value.svg.txt)

```json
<svg id="Capa_1" enable-background="new 0 0 510.586 510.586" height="512" viewBox="0 0 510.586 510.586" width="512" xmlns="http://www.w3.org/2000/svg"><g><g><circle cx="260.906" cy="105.508" fill="#ade194" r="67.956"/><path d="m229.566 105.508c0-31.185 21.014-57.445 49.648-65.44-5.827-1.627-11.962-2.516-18.308-2.516-37.531 0-67.956 30.425-67.956 67.956s30.425 67.957 67.956 67.957c6.346 0 12.481-.889 18.308-2.516-28.635-7.996-49.648-34.256-49.648-65.441z" fill="#97da7b"/><g><g id="XMLID_559_"><g>
```

### `GET /casino/banner/images/sports-icons.png`
- **Full URL**: `https://images.staticcontents.net/casino/banner/images/sports-icons.png`
- **Status**: `200`
- **Content-Type**: `image/png`
- **Saved Payload**: [`GET_images.staticcontents.net__casino_banner_images_sports-icons.png.txt`](./responses/GET_images.staticcontents.net__casino_banner_images_sports-icons.png.txt)

```json
PNG

   IHDR     !      	pHYs       iTXtXML:com.adobe.xmp     <?xpacket begin="﻿" id="W5M0MpCehiHzreSzNTczkc9d"?> <x:xmpmeta xmlns:x="adobe:ns:meta/" x:xmptk="Adobe XMP Core 9.0-c001 79.14ecb42, 2022/12/02-19:12:44        "> <rdf:RDF xmlns:rdf="http://www.w3.org/1999/02/22-rdf-syntax-ns#"> <rdf:Description rdf:about="" xmlns:xmp="http://ns.adobe.com/xap/1.0/" xmlns:dc="http://purl.org/dc/elements/1.1/" xmlns:photoshop="http://ns.adobe.com/photoshop/1.0/" xmlns:xmpMM="http://ns.adobe.
```

### `GET /casino/banner/images/unsettle-bet.svg`
- **Full URL**: `https://images.staticcontents.net/casino/banner/images/unsettle-bet.svg`
- **Status**: `200`
- **Content-Type**: `image/svg+xml`
- **Saved Payload**: [`GET_images.staticcontents.net__casino_banner_images_unsettle-bet.svg.txt`](./responses/GET_images.staticcontents.net__casino_banner_images_unsettle-bet.svg.txt)

```json
<svg id="Capa_1" enable-background="new 0 0 512 512" height="512" viewBox="0 0 512 512" width="512" xmlns="http://www.w3.org/2000/svg"><g><g><g><g><g><g><g><g><g><g><g><path d="m415.551 35.326h-319.102c-13.802 0-24.991 11.189-24.991 24.991v419.192c0 13.802 11.189 24.991 24.991 24.991h319.102c13.802 0 24.991-11.189 24.991-24.991v-419.192c0-13.802-11.189-24.991-24.991-24.991z" fill="#f8e8bb"/><path d="m415.551 35.326h-27.704v469.174h27.704c13.802 0 24.991-11.189 24.991-24.991v-419.192c0-13.802-11.
```

### `GET /casino/banner/loginimages/Evoplay.png`
- **Full URL**: `https://images.staticcontents.net/casino/banner/loginimages/Evoplay.png`
- **Status**: `200`
- **Content-Type**: `image/png`
- **Saved Payload**: [`GET_images.staticcontents.net__casino_banner_loginimages_Evoplay.png.txt`](./responses/GET_images.staticcontents.net__casino_banner_loginimages_Evoplay.png.txt)

```json
PNG

   IHDR      6   %`   sRGB    	pHYs       YiTXtXML:com.adobe.xmp     <x:xmpmeta xmlns:x="adobe:ns:meta/" x:xmptk="XMP Core 5.4.0">
   <rdf:RDF xmlns:rdf="http://www.w3.org/1999/02/22-rdf-syntax-ns#">
      <rdf:Description rdf:about=""
            xmlns:tiff="http://ns.adobe.com/tiff/1.0/">
         <tiff:Orientation>1</tiff:Orientation>
      </rdf:Description>
   </rdf:RDF>
</x:xmpmeta>
L'Y  IDATxp]u9%ْ<$#إ Iy;	IiJt&-nCy0t(u)ӒLSBhjk ``L(T6`l\[֕dY}{%C]u>{k9N
```

### `GET /casino/banner/loginimages/betgames.png`
- **Full URL**: `https://images.staticcontents.net/casino/banner/loginimages/betgames.png`
- **Status**: `200`
- **Content-Type**: `image/png`
- **Saved Payload**: [`GET_images.staticcontents.net__casino_banner_loginimages_betgames.png.txt`](./responses/GET_images.staticcontents.net__casino_banner_loginimages_betgames.png.txt)

```json
PNG

   IHDR      #   v$  IDATx]UyZGm&sgHkŶU[bds'.j]U",UEA4bh)X<ܳ̄&3ݜ̬ugsVm8%K6,98Px#쳷n<Z'Ͻ+[vv{ t#te1^"cA.<l.<'zwS˗>8ZmEOQ	TaLKќEcT"ȿ;FZ=խjϪVs$i|xꖖΪmKnWK7>%`ԜCq\Zժ5jhGAA&3R SVeUfAYz!})WSOҁgl*(X4ٶwQEiODL (cLAvWk۪jZ8'@&J<<zi WDY=TM
%Q	4zO ;Ug!xb}Dj"6?4X0ݫ0q	1#R?%X.Ud{gdJ?GZO7MD$2j"*E
^ժ
bz'hôP3
b(o	8SŁMſ^xN*V=}WfΚں\'Tm8 z괅2u	4N a2w	u<AӟkPHɣ,k<\'?Mx.Am2f8x*iqX.>N|rgs~	Ucbjl,ڮթ9W	jxe zءXL:|r\w wAn#%
```

### `GET /casino/banner/loginimages/betsoft.png`
- **Full URL**: `https://images.staticcontents.net/casino/banner/loginimages/betsoft.png`
- **Status**: `200`
- **Content-Type**: `image/png`
- **Saved Payload**: [`GET_images.staticcontents.net__casino_banner_loginimages_betsoft.png.txt`](./responses/GET_images.staticcontents.net__casino_banner_loginimages_betsoft.png.txt)

```json
PNG

   IHDR      F   .?m   sRGB    	pHYs       iTXtXML:com.adobe.xmp     <x:xmpmeta xmlns:x="adobe:ns:meta/" x:xmptk="XMP Core 5.4.0">
   <rdf:RDF xmlns:rdf="http://www.w3.org/1999/02/22-rdf-syntax-ns#">
      <rdf:Description rdf:about=""
            xmlns:xmp="http://ns.adobe.com/xap/1.0/"
            xmlns:tiff="http://ns.adobe.com/tiff/1.0/"
            xmlns:exif="http://ns.adobe.com/exif/1.0/">
         <xmp:ModifyDate>2020-06-16T14:06:81</xmp:ModifyDate>
         <xmp:Creat
```

### `GET /casino/banner/loginimages/evolution.png`
- **Full URL**: `https://images.staticcontents.net/casino/banner/loginimages/evolution.png`
- **Status**: `200`
- **Content-Type**: `image/png`
- **Saved Payload**: [`GET_images.staticcontents.net__casino_banner_loginimages_evolution.png.txt`](./responses/GET_images.staticcontents.net__casino_banner_loginimages_evolution.png.txt)

```json
PNG

   IHDR      (      sRGB    eXIfMM *                  V       ^(       1       fi       |       H      H   Pixelmator Pro 1.6.4                               (    2020:07:01 10:17:36 =Y   	pHYs       iTXtXML:com.adobe.xmp     <x:xmpmeta xmlns:x="adobe:ns:meta/" x:xmptk="XMP Core 5.4.0">
   <rdf:RDF xmlns:rdf="http://www.w3.org/1999/02/22-rdf-syntax-ns#">
      <rdf:Description rdf:about=""
            xmlns:tiff="http://ns.adobe.com/
```

### `GET /casino/banner/loginimages/ezugi.png`
- **Full URL**: `https://images.staticcontents.net/casino/banner/loginimages/ezugi.png`
- **Status**: `200`
- **Content-Type**: `image/png`
- **Saved Payload**: [`GET_images.staticcontents.net__casino_banner_loginimages_ezugi.png.txt`](./responses/GET_images.staticcontents.net__casino_banner_loginimages_ezugi.png.txt)

```json
PNG

   IHDR   s   -   Ta  ]IDATx[Uy~{B,kXkN^Zmmm;:Z*j[R[ !r^w};4gf|{}8[RPmv^Uݪ~^d5yGbw^/yathEcdt4Aja`cq%{R[qKW#"|X5 0(5ys'JI8{j3Y\[:/v˛nmF饥_Ձ}Gr/buͪe%SQupͱ^EGR)"]|Pӗay㉻A4'M
bWT⥀%ITu AU`BU]crlWsQ`̤)-OF+&/Lʋ|-h*sHŇStz
OR*D ܾܺoyPnh\8h1$H̅3SDQo%\/vpY 9 <	=C<@3LS#!T&>g#Zh.+d']IIdIz$.-Qp] 	^=.79 ֚c`.+
@MUx8tgPUE$R5 XWE\&LUr'I+`RrF0쪎.;R/>{pxWa*uKrXV>,-9SE3SuPAd>y)m$ xRU?#dU=3ۡ;w
```

### `GET /casino/banner/loginimages/logo-18plus.svg`
- **Full URL**: `https://images.staticcontents.net/casino/banner/loginimages/logo-18plus.svg`
- **Status**: `200`
- **Content-Type**: `image/svg+xml`
- **Saved Payload**: [`GET_images.staticcontents.net__casino_banner_loginimages_logo-18plus.svg.txt`](./responses/GET_images.staticcontents.net__casino_banner_loginimages_logo-18plus.svg.txt)

```json
<svg width="36" height="36" viewBox="0 0 36 36" fill="none" xmlns="http://www.w3.org/2000/svg">
<circle cx="18" cy="18" r="17.5" stroke="#9B9B9B"/>
<path d="M10.7441 17.4287H13.2119V19.2129H10.7441V22.002H8.86426V19.2129H6.38965V17.4287H8.86426V14.7559H10.7441V17.4287ZM19.1182 23H17.1426V15.3848L14.7842 16.1162V14.5098L18.9062 13.0332H19.1182V23ZM28.8457 15.6924C28.8457 16.1755 28.7249 16.6038 28.4834 16.9775C28.2419 17.3512 27.9092 17.6497 27.4854 17.873C27.9684 18.1055 28.3512 18.4268 28.6338 
```

### `GET /casino/banner/loginimages/mobile/betgames.svg`
- **Full URL**: `https://images.staticcontents.net/casino/banner/loginimages/mobile/betgames.svg`
- **Status**: `200`
- **Content-Type**: `image/svg+xml`
- **Saved Payload**: [`GET_images.staticcontents.net__casino_banner_loginimages_mobile_betgames.svg.txt`](./responses/GET_images.staticcontents.net__casino_banner_loginimages_mobile_betgames.svg.txt)

```json
<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE svg PUBLIC "-//W3C//DTD SVG 1.1//EN" "http://www.w3.org/Graphics/SVG/1.1/DTD/svg11.dtd">
<!-- Creator: CorelDRAW X7 -->
<svg xmlns="http://www.w3.org/2000/svg" xml:space="preserve" width="21.1666mm" height="8.4666mm" version="1.1" style="shape-rendering:geometricPrecision; text-rendering:geometricPrecision; image-rendering:optimizeQuality; fill-rule:evenodd; clip-rule:evenodd"
viewBox="0 0 2117 847"
 xmlns:xlink="http://www.w3.org/1999/xlink"
```

### `GET /casino/banner/loginimages/mobile/betsoft.svg`
- **Full URL**: `https://images.staticcontents.net/casino/banner/loginimages/mobile/betsoft.svg`
- **Status**: `200`
- **Content-Type**: `image/svg+xml`
- **Saved Payload**: [`GET_images.staticcontents.net__casino_banner_loginimages_mobile_betsoft.svg.txt`](./responses/GET_images.staticcontents.net__casino_banner_loginimages_mobile_betsoft.svg.txt)

```json
<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE svg PUBLIC "-//W3C//DTD SVG 1.1//EN" "http://www.w3.org/Graphics/SVG/1.1/DTD/svg11.dtd">
<!-- Creator: CorelDRAW X7 -->
<svg xmlns="http://www.w3.org/2000/svg" xml:space="preserve" width="21.1666mm" height="8.4666mm" version="1.1" style="shape-rendering:geometricPrecision; text-rendering:geometricPrecision; image-rendering:optimizeQuality; fill-rule:evenodd; clip-rule:evenodd"
viewBox="0 0 2117 847"
 xmlns:xlink="http://www.w3.org/1999/xlink"
```

### `GET /casino/banner/loginimages/mobile/evolution.svg`
- **Full URL**: `https://images.staticcontents.net/casino/banner/loginimages/mobile/evolution.svg`
- **Status**: `200`
- **Content-Type**: `image/svg+xml`
- **Saved Payload**: [`GET_images.staticcontents.net__casino_banner_loginimages_mobile_evolution.svg.txt`](./responses/GET_images.staticcontents.net__casino_banner_loginimages_mobile_evolution.svg.txt)

```json
<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE svg PUBLIC "-//W3C//DTD SVG 1.1//EN" "http://www.w3.org/Graphics/SVG/1.1/DTD/svg11.dtd">
<!-- Creator: CorelDRAW X7 -->
<svg xmlns="http://www.w3.org/2000/svg" xml:space="preserve" width="21.1666mm" height="8.4666mm" version="1.1" style="shape-rendering:geometricPrecision; text-rendering:geometricPrecision; image-rendering:optimizeQuality; fill-rule:evenodd; clip-rule:evenodd"
viewBox="0 0 2117 847"
 xmlns:xlink="http://www.w3.org/1999/xlink"
```

### `GET /casino/banner/loginimages/mobile/evoplay.svg`
- **Full URL**: `https://images.staticcontents.net/casino/banner/loginimages/mobile/evoplay.svg`
- **Status**: `200`
- **Content-Type**: `image/svg+xml`
- **Saved Payload**: [`GET_images.staticcontents.net__casino_banner_loginimages_mobile_evoplay.svg.txt`](./responses/GET_images.staticcontents.net__casino_banner_loginimages_mobile_evoplay.svg.txt)

```json
<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE svg PUBLIC "-//W3C//DTD SVG 1.1//EN" "http://www.w3.org/Graphics/SVG/1.1/DTD/svg11.dtd">
<!-- Creator: CorelDRAW X7 -->
<svg xmlns="http://www.w3.org/2000/svg" xml:space="preserve" width="21.1666mm" height="8.4666mm" version="1.1" style="shape-rendering:geometricPrecision; text-rendering:geometricPrecision; image-rendering:optimizeQuality; fill-rule:evenodd; clip-rule:evenodd"
viewBox="0 0 2117 847"
 xmlns:xlink="http://www.w3.org/1999/xlink"
```

### `GET /casino/banner/loginimages/mobile/ezugi.svg`
- **Full URL**: `https://images.staticcontents.net/casino/banner/loginimages/mobile/ezugi.svg`
- **Status**: `200`
- **Content-Type**: `image/svg+xml`
- **Saved Payload**: [`GET_images.staticcontents.net__casino_banner_loginimages_mobile_ezugi.svg.txt`](./responses/GET_images.staticcontents.net__casino_banner_loginimages_mobile_ezugi.svg.txt)

```json
<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE svg PUBLIC "-//W3C//DTD SVG 1.1//EN" "http://www.w3.org/Graphics/SVG/1.1/DTD/svg11.dtd">
<!-- Creator: CorelDRAW X7 -->
<svg xmlns="http://www.w3.org/2000/svg" xml:space="preserve" width="21.1666mm" height="8.4666mm" version="1.1" style="shape-rendering:geometricPrecision; text-rendering:geometricPrecision; image-rendering:optimizeQuality; fill-rule:evenodd; clip-rule:evenodd"
viewBox="0 0 2117 847"
 xmlns:xlink="http://www.w3.org/1999/xlink"
```

### `GET /casino/banner/loginimages/mobile/logo-18plus.svg`
- **Full URL**: `https://images.staticcontents.net/casino/banner/loginimages/mobile/logo-18plus.svg`
- **Status**: `200`
- **Content-Type**: `image/svg+xml`
- **Saved Payload**: [`GET_images.staticcontents.net__casino_banner_loginimages_mobile_logo-18plus.svg.txt`](./responses/GET_images.staticcontents.net__casino_banner_loginimages_mobile_logo-18plus.svg.txt)

```json
<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE svg PUBLIC "-//W3C//DTD SVG 1.1//EN" "http://www.w3.org/Graphics/SVG/1.1/DTD/svg11.dtd">
<!-- Creator: CorelDRAW X7 -->
<svg xmlns="http://www.w3.org/2000/svg" xml:space="preserve" width="5.5032mm" height="5.5032mm" version="1.1" style="shape-rendering:geometricPrecision; text-rendering:geometricPrecision; image-rendering:optimizeQuality; fill-rule:evenodd; clip-rule:evenodd"
viewBox="0 0 550 550"
 xmlns:xlink="http://www.w3.org/1999/xlink">
```

### `GET /casino/banner/loginimages/mobile/pragmatic.svg`
- **Full URL**: `https://images.staticcontents.net/casino/banner/loginimages/mobile/pragmatic.svg`
- **Status**: `200`
- **Content-Type**: `image/svg+xml`
- **Saved Payload**: [`GET_images.staticcontents.net__casino_banner_loginimages_mobile_pragmatic.svg.txt`](./responses/GET_images.staticcontents.net__casino_banner_loginimages_mobile_pragmatic.svg.txt)

```json
<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE svg PUBLIC "-//W3C//DTD SVG 1.1//EN" "http://www.w3.org/Graphics/SVG/1.1/DTD/svg11.dtd">
<!-- Creator: CorelDRAW X7 -->
<svg xmlns="http://www.w3.org/2000/svg" xml:space="preserve" width="21.1666mm" height="8.4666mm" version="1.1" style="shape-rendering:geometricPrecision; text-rendering:geometricPrecision; image-rendering:optimizeQuality; fill-rule:evenodd; clip-rule:evenodd"
viewBox="0 0 2117 847"
 xmlns:xlink="http://www.w3.org/1999/xlink"
```

### `GET /casino/banner/loginimages/mobile/spribe.svg`
- **Full URL**: `https://images.staticcontents.net/casino/banner/loginimages/mobile/spribe.svg`
- **Status**: `200`
- **Content-Type**: `image/svg+xml`
- **Saved Payload**: [`GET_images.staticcontents.net__casino_banner_loginimages_mobile_spribe.svg.txt`](./responses/GET_images.staticcontents.net__casino_banner_loginimages_mobile_spribe.svg.txt)

```json
<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE svg PUBLIC "-//W3C//DTD SVG 1.1//EN" "http://www.w3.org/Graphics/SVG/1.1/DTD/svg11.dtd">
<!-- Creator: CorelDRAW X7 -->
<svg xmlns="http://www.w3.org/2000/svg" xml:space="preserve" width="21.1666mm" height="8.4666mm" version="1.1" style="shape-rendering:geometricPrecision; text-rendering:geometricPrecision; image-rendering:optimizeQuality; fill-rule:evenodd; clip-rule:evenodd"
viewBox="0 0 2117 847"
 xmlns:xlink="http://www.w3.org/1999/xlink"
```

### `GET /casino/banner/loginimages/mobile/superspade.svg`
- **Full URL**: `https://images.staticcontents.net/casino/banner/loginimages/mobile/superspade.svg`
- **Status**: `200`
- **Content-Type**: `image/svg+xml`
- **Saved Payload**: [`GET_images.staticcontents.net__casino_banner_loginimages_mobile_superspade.svg.txt`](./responses/GET_images.staticcontents.net__casino_banner_loginimages_mobile_superspade.svg.txt)

```json
<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE svg PUBLIC "-//W3C//DTD SVG 1.1//EN" "http://www.w3.org/Graphics/SVG/1.1/DTD/svg11.dtd">
<!-- Creator: CorelDRAW X7 -->
<svg xmlns="http://www.w3.org/2000/svg" xml:space="preserve" width="21.1666mm" height="8.4666mm" version="1.1" style="shape-rendering:geometricPrecision; text-rendering:geometricPrecision; image-rendering:optimizeQuality; fill-rule:evenodd; clip-rule:evenodd"
viewBox="0 0 2117 847"
 xmlns:xlink="http://www.w3.org/1999/xlink"
```

### `GET /casino/banner/loginimages/pragmatic-live.png`
- **Full URL**: `https://images.staticcontents.net/casino/banner/loginimages/pragmatic-live.png`
- **Status**: `200`
- **Content-Type**: `image/png`
- **Saved Payload**: [`GET_images.staticcontents.net__casino_banner_loginimages_pragmatic-live.png.txt`](./responses/GET_images.staticcontents.net__casino_banner_loginimages_pragmatic-live.png.txt)

```json
PNG

   IHDR      G   ch   	pHYs        sRGB    gAMA  a  IDATx]xUՕ^{s "ZS)OZ 
HPVkUXeįCNg,
Z;A| 	!	}䞳{%%!묵y<ɚHQAn
C=cJ=\1l$0xf(X4UE*ּxH%#1n/Y*XVt6/l$c,Ck|D\Zי_[1WV^#c,4m\t7Y?r<r1HPzFBjEEyQRT2xK{ʳؑԏs>l&r<nGCUNˇd'|,cxLS2xP7Uedz,]n	l--+1zVHGEo"fi#Gn #Eߦ-Uј"<X?|^d5β̄Lsؾv֫ٳk&rX1\Vd.ڢP9tQ5Ex$3ry3*tr#(2.m]eePS5QdA{1E.X.D][yfRj ?4(e6-jkel,G{yv~GsfTN.X.g*$S?UOt(%l1cc:GF_cALUo^גdXu#T醓ؾ9j-z`Wײ6P
```

### `GET /casino/banner/loginimages/spribe.png`
- **Full URL**: `https://images.staticcontents.net/casino/banner/loginimages/spribe.png`
- **Status**: `200`
- **Content-Type**: `image/png`
- **Saved Payload**: [`GET_images.staticcontents.net__casino_banner_loginimages_spribe.png.txt`](./responses/GET_images.staticcontents.net__casino_banner_loginimages_spribe.png.txt)

```json
PNG

   IHDR  ]      i   	pHYs       iTXtXML:com.adobe.xmp     <?xpacket begin="﻿" id="W5M0MpCehiHzreSzNTczkc9d"?> <x:xmpmeta xmlns:x="adobe:ns:meta/" x:xmptk="Adobe XMP Core 9.0-c001 79.14ecb42, 2022/12/02-19:12:44        "> <rdf:RDF xmlns:rdf="http://www.w3.org/1999/02/22-rdf-syntax-ns#"> <rdf:Description rdf:about="" xmlns:xmp="http://ns.adobe.com/xap/1.0/" xmlns:dc="http://purl.org/dc/elements/1.1/" xmlns:photoshop="http://ns.adobe.com/photoshop/1.0/" xmlns:xmpMM="http://ns.adob
```

### `GET /casino/banner/loginimages/ssg.png`
- **Full URL**: `https://images.staticcontents.net/casino/banner/loginimages/ssg.png`
- **Status**: `200`
- **Content-Type**: `image/png`
- **Saved Payload**: [`GET_images.staticcontents.net__casino_banner_loginimages_ssg.png.txt`](./responses/GET_images.staticcontents.net__casino_banner_loginimages_ssg.png.txt)

```json
PNG

   IHDR   x   x   9d6   sRGB    	pHYs       iTXtXML:com.adobe.xmp     <x:xmpmeta xmlns:x="adobe:ns:meta/" x:xmptk="XMP Core 5.4.0">
   <rdf:RDF xmlns:rdf="http://www.w3.org/1999/02/22-rdf-syntax-ns#">
      <rdf:Description rdf:about=""
            xmlns:xmp="http://ns.adobe.com/xap/1.0/"
            xmlns:tiff="http://ns.adobe.com/tiff/1.0/"
            xmlns:exif="http://ns.adobe.com/exif/1.0/">
         <xmp:ModifyDate>2020-11-21T18:11:65</xmp:ModifyDate>
         <xmp:Crea
```

### `GET /casino/banner/mobiledefaultbanner.jpg`
- **Full URL**: `https://images.staticcontents.net/casino/banner/mobiledefaultbanner.jpg`
- **Status**: `200`
- **Content-Type**: `image/jpeg`
- **Saved Payload**: [`GET_images.staticcontents.net__casino_banner_mobiledefaultbanner.jpg.txt`](./responses/GET_images.staticcontents.net__casino_banner_mobiledefaultbanner.jpg.txt)

```json
Exif  MM *                  b       j(       1       r2       i           
  ' 
  'Adobe Photoshop 21.0 (Windows) 2022:04:20 22:32:55                         ,                    "      *(             2             H      H    Adobe_CM  Adobe d     			
  ? "   
?          
```

### `GET /evts/winnereventdic.json`
- **Full URL**: `https://images.staticcontents.net/evts/winnereventdic.json?1793734929362`
- **Status**: `200`
- **Content-Type**: `application/json`
- **Saved Payload**: [`GET_images.staticcontents.net__evts_winnereventdic.json.json`](./responses/GET_images.staticcontents.net__evts_winnereventdic.json.json)

```json
{
  "eventDicByName": {
    "wbbl": {
      "url": "/wbbl",
      "displayName": "WBBL 2026",
      "eventid": 28045743,
      "selectedMarket": 1.26373753,
      "eventtype": 4,
      "showInMenu": true,
      "show": true
    },
    "bbl": {
      "url": "/bbl",
      "displayName": "BBL 2025",
      "eventid": 27996014,
      "selectedMarket": 0,
      "eventtype": 4,
      "showInMenu": true,
      "show": false
    },
    "psl": {
      "url": "/psl",
      "displayName": "PSL 2026",
      "eventid": 28102621,
      "selectedMarket": 1.221643851,
      "eventtype": 4,
      "showInMenu": true,
      "show": false
    },
    "wc": {
      "url": "/wc",
      "displayName": "World Cup",
      "eventid": 29371262,
      "selectedMarket": 1.160513989,
      "eventtype": 4,
      "showInMe
```

### `GET /rde/banners/SocialMediaAndNumbers.json`
- **Full URL**: `https://images.staticcontents.net/rde/banners/SocialMediaAndNumbers.json`
- **Status**: `200`
- **Content-Type**: `text/json`
- **Saved Payload**: [`GET_images.staticcontents.net__rde_banners_SocialMediaAndNumbers.json.json`](./responses/GET_images.staticcontents.net__rde_banners_SocialMediaAndNumbers.json.json)

```json
{
  "ALLPAGEDISPLAYWHATSAPP": "",
  "ALLPAGEDISPLAYTELEGRAM": "",
  "ALLPAGEDISPLAYWHATSAPPACCOUNT": "",
  "ALLPAGEDISPLAYWHATSAPPSUPPORT": "",
  "ALLPAGEDISPLAYFEEDBACKWHATSAPPT": "",
  "ALLPAGEDISPLAYFEEDBACKEMAIL": "",
  "SOCIALMEDIALINKS": {
    "whatsapp": "#",
    "facebook": "#",
    "twitter": "#",
    "instagram": "#",
    "youtube": "#",
    "telegram": "#",
    "whatsappDisplayNumber": "#"
  }
}
```

### `GET /rde/banners/list.json`
- **Full URL**: `https://images.staticcontents.net/rde/banners/list.json`
- **Status**: `200`
- **Content-Type**: `binary/octet-stream`
- **Saved Payload**: [`GET_images.staticcontents.net__rde_banners_list.json.json`](./responses/GET_images.staticcontents.net__rde_banners_list.json.json)

```json
{
  "desktop": [],
  "mobile": []
}
```

### `GET /rde/banners/listwologin.json`
- **Full URL**: `https://images.staticcontents.net/rde/banners/listwologin.json`
- **Status**: `200`
- **Content-Type**: `binary/octet-stream`
- **Saved Payload**: [`GET_images.staticcontents.net__rde_banners_listwologin.json.json`](./responses/GET_images.staticcontents.net__rde_banners_listwologin.json.json)

```json
{
  "maindesktopwologin": [
    "0.webp",
    "1.webp",
    "2.webp",
    "3.webp",
    "4.webp",
    "5.webp"
  ],
  "mainmobilewologin": [
    "0.webp",
    "1.webp",
    "2.webp",
    "3.webp",
    "4.webp",
    "5.webp"
  ],
  "bonuswologin": [
    "1.webp",
    "2.webp",
    "3.webp"
  ],
  "gifwologin": [
    "1.gif",
    "2.gif"
  ]
}
```

### `GET /rde/login/main-banner-mobile0.webp`
- **Full URL**: `https://images.staticcontents.net/rde/login/main-banner-mobile0.webp`
- **Status**: `200`
- **Content-Type**: `image/webp`
- **Saved Payload**: [`GET_images.staticcontents.net__rde_login_main-banner-mobile0.webp.txt`](./responses/GET_images.staticcontents.net__rde_login_main-banner-mobile0.webp.txt)

```json
RIFFx WEBPVP8X
       + VP8 9 * ,   %e8dpFZOȧf+n۽wʧ?3gsbGo?}y3O_~Ck}~/#nms/}6kKW=go_W/?i{??>[f5?0#d/߮5O?@-#O8cO3_>?OޒGO??q7}3T|K/kGj}$ugo_o?c_̿r-K_y}~6\W\ݎ/B~˙D\6F㿁&?*"Otc2fw%u_xwI<6]pHګ+řx4b&{>f"oI{G[l4>ZkCS֗aR1}jzKbLÓyb1Pkb,vJE!y6DQtCs)C3vwz(n#+(f W;: Wqm;!q19I!へp`:@qH%u'=**aA(ENk_%j3:߹6@$4MKj	/ &)A2+{5O5Rd0!l٨Ks&7bB ^s0oV+Ot,[k,Ny3$(;|VRКIKo^c2Gx)r.iD"u_9+u//%܍GTb:jJA*
```

### `GET /rde/login/main-banner-mobile1.webp`
- **Full URL**: `https://images.staticcontents.net/rde/login/main-banner-mobile1.webp`
- **Status**: `200`
- **Content-Type**: `image/webp`
- **Saved Payload**: [`GET_images.staticcontents.net__rde_login_main-banner-mobile1.webp.txt`](./responses/GET_images.staticcontents.net__rde_login_main-banner-mobile1.webp.txt)

```json
RIFF{ WEBPVP8X
       + VP8 .< n* ,   %~ʅ7儠9p`Gt{Yo߱O=Ny?}m_r{yO߷?On~?9?c'xt'w?ͯ?Y_?2?)}sO_-gWoo'W? ?{e U~]GYh+'淹Ⱦ_ڟe??W_?⿴j{?Cs)ww!=cg_G3C˿qq#|?۟`_?zw_oK7_?gwr_X~{G; N߼n?	iPLjdyP$Wy,+ɳ-)i

l+WsN胃,w-QrT1g{n²`imDgoĚIea t-:j,x|@ٿ'ȮOR9\d c!FS ~1mrʻpxhPwP3/UB1CZZeCfK["`bW]JVT<U/^rO/Khe/i>
ZD^	b32k!!<)\2GR"^F5th%yBk)-XDoͶ맕`KK શZ?EYgKBaTg'}-@CzCGE,5,+_ii;ϱnx	8wdyyIvkb.=}(y4
```

### `GET /rde/login/main-banner-mobile2.webp`
- **Full URL**: `https://images.staticcontents.net/rde/login/main-banner-mobile2.webp`
- **Status**: `200`
- **Content-Type**: `image/webp`
- **Saved Payload**: [`GET_images.staticcontents.net__rde_login_main-banner-mobile2.webp.txt`](./responses/GET_images.staticcontents.net__rde_login_main-banner-mobile2.webp.txt)

```json
RIFF< WEBPVP8X
   (    + ICCP
    
lcms0  mntrRGB XYZ      acspMSFT    lcms                       -lcms                                               dmnd     jdesc     hdmdd     hwtpt  P   rXYZ  d   bXYZ  x   gXYZ     rTRC    gTRC  
  bTRC    chrm     $cprt     !desc       lcms generated                                                                                  desc       sRGB                                                                            
```

### `GET /rde/login/main-banner-mobile3.webp`
- **Full URL**: `https://images.staticcontents.net/rde/login/main-banner-mobile3.webp`
- **Status**: `200`
- **Content-Type**: `image/webp`
- **Saved Payload**: [`GET_images.staticcontents.net__rde_login_main-banner-mobile3.webp.txt`](./responses/GET_images.staticcontents.net__rde_login_main-banner-mobile3.webp.txt)

```json
RIFF WEBPVP8X
       + VP8 &K P=* ,   %3+=f+*?L	g[y@3S?ofdû_/(NW׷t:W|Voyg?3/c壍W_?~Xu?~;y'?;?}?[COO?;>3_#?_ʿ}wG˿_'/Ekg_?3O^?r=l<{u}c追=o?zݏd[_{+/ܿx[k7YO?/Ϟyo쾶~vz1o??i? F)??c;/?=/_?O_?KO_Ho?{s1%Og-kꄕSO+B!:&X		tM"s~'YcbEF%јdݨM~x*UCXe5o!eяx~_06x&38޼4jAܨ{lEvRӟKW"$Tߋ\B!s-'5k!OŦ}?cdֱ`1hWzs0ﮫHz-xUᬀ_@]_Jsv7Ѫlx&?O8*6tX)".	?] GXE/ik&Zn]|:6ӧ[UM'2[yk*i(E %BGiRɧkak˅$Hbܲ{q(gc;]w;	n`(x!Hύ.~
```

### `GET /rde/login/main-banner-mobile4.webp`
- **Full URL**: `https://images.staticcontents.net/rde/login/main-banner-mobile4.webp`
- **Status**: `200`
- **Content-Type**: `image/webp`
- **Saved Payload**: [`GET_images.staticcontents.net__rde_login_main-banner-mobile4.webp.txt`](./responses/GET_images.staticcontents.net__rde_login_main-banner-mobile4.webp.txt)

```json
RIFFJ WEBPVP8X
       + VP8 jn 0Z* ,   %+	$9;sG=4YS_ĤĆ&=_;i~xOǿ@09~ Iod{*qM~X?g?}? =|_??'u~O})O_V?{}3Wr>߿?_?w?ο/?'?W/_ߚ ?{P {3W篵ߪ翼sysSx)=woi>_7oG_iU/}ͷ?a|{U?zGUw'+_CgWK~O{?!7?'/>?nܔTJ8lkU'$[Z҇s[.$ZyUFFRƆIiO<W~={q;}_bi2oLz[^@=a;ks;N5,ڽP^_N [m17mНK4 E0BNwSh7sM1,nd7,A@FHj"I>eEX*QnT5_c](,a`օ1*(3yW/Iݡ2-9`\]s*a
7ß7vR =B-uoDbyqC=GE6e33X);D8:gƗK8?ϡy*dc8[?HX'	.Oc SMk3<LLMX}Bb
```

### `GET /rde/login/main-banner-mobile5.webp`
- **Full URL**: `https://images.staticcontents.net/rde/login/main-banner-mobile5.webp`
- **Status**: `200`
- **Content-Type**: `image/webp`
- **Saved Payload**: [`GET_images.staticcontents.net__rde_login_main-banner-mobile5.webp.txt`](./responses/GET_images.staticcontents.net__rde_login_main-banner-mobile5.webp.txt)

```json
RIFFl WEBPVP8X
       + VP8 -  * ,   %=E/y7t!Ote7c#]wn^q[wu_ n{ ~ z~K:>}f.7=Y?cA?_t7?s?'kܟo?W? p~|y?/OS ?};o}ÿ{#~oOOڿ go?]'vy3?{>?3/忲gG;#ԿeU[_<?9??~|G/E{>V_˯wgO	Os?m/oo+}tY~n~Va~3pLhnk7WxI❋X]\,l= .vD/i'q0$q-7B/-hζyZ"=>
MP/\4QHy}I+%UWlaJk?E-A2`=URRd	FPYWZ(Zy@8`#ZGȰcu1y({J;"NbS[$ugr]}Y%bz>.j=M풬LZ'b{S.|P=<\p\&N0ܹ6iҴKdH^QGExY.T&^:D3_o .\N
7zu]V(t uXh6Ь"KJX,SǑ
c=-Bn;*ԊMD|Ҷ+D
```

### `GET /rde/login/main-banner0.webp`
- **Full URL**: `https://images.staticcontents.net/rde/login/main-banner0.webp`
- **Status**: `200`
- **Content-Type**: `image/webp`
- **Saved Payload**: [`GET_images.staticcontents.net__rde_login_main-banner0.webp.txt`](./responses/GET_images.staticcontents.net__rde_login_main-banner0.webp.txt)

```json
RIFF WEBPVP8X
       { ALPH    Hu 
H0ILiD3?????????xVP8   *|>DJ.$1j	enܡeBfQx<`!B^-9q/Das,I7ro_3{~SGmc쇬u='=i?WPlƾgךz#O
'Fa?b.^n8iAT*:ײJOM^d3+s6lWsX#_2u9QV'abSڝ\0:IoIyk+g(LfFZZܡ@.3%~ ^κ-xH1T֮k3ܵ$gQnZ3;5~)dn( xˍ%*V@_jzW~vHHOِ?kqr170}Q1sfzMrePW/~](vsJsǾ&KոD!kO1}(i9`8{+db;0\5U3;ϐJhdxzk3
:$@.\Ws?Q)n诹SӼB8]~TT@0g8E6LΈ񕾏Sƨ	jNE5ώ`
M1yXʙN%} 9	q<*|*qWrEJ1_t`m*-mcw)X,zS"1~]w/snFb-4t5CN@΢)nBJ(.x&C 
```

### `GET /rde/login/main-banner1.webp`
- **Full URL**: `https://images.staticcontents.net/rde/login/main-banner1.webp`
- **Status**: `200`
- **Content-Type**: `image/webp`
- **Saved Payload**: [`GET_images.staticcontents.net__rde_login_main-banner1.webp.txt`](./responses/GET_images.staticcontents.net__rde_login_main-banner1.webp.txt)

```json
RIFF~ WEBPVP8 r 0*|>FJ%&T
:	en:dy1p2f6# uCm]=Mo>f;=vῑ[Me/?v	O/Cڏ>_~T/ I:}#??}kW/,7mO9$Z;9KX"u<<Y>ߴ~Oc`;Y[Z/`L%0z1l[vNԟ{d]Q=w43&4[Edx<m9nUa	0JNRɗ?_#"SJlkHA/a#se+=%7)
olE
NK}'FY~oJMu:HxKRdeB95mbT)%_'U+7(JxE%]wf*]QDlP"\T1{K4`I 
R`h* uOm`:ک?Z-xЩ-PuE7|jrnD4vpn+N^ۋ
>gXB[9ĤߚoFL`gYp)4kΐk]'U	߂G7
{ ?J81Imvgւj=<ɷxQZ;Wz?}37%n8u˒H&Bf;.lJAt& F }gu8&}C":SLsi֜m47ݕ0MS%II2vT9s2<OVw6G A$ &PܶB5PqYxg.> We-VC%KW
```

### `GET /rde/login/main-banner2.webp`
- **Full URL**: `https://images.staticcontents.net/rde/login/main-banner2.webp`
- **Status**: `200`
- **Content-Type**: `image/webp`
- **Saved Payload**: [`GET_images.staticcontents.net__rde_login_main-banner2.webp.txt`](./responses/GET_images.staticcontents.net__rde_login_main-banner2.webp.txt)

```json
RIFF WEBPVP8X
   (    { ICCP
    
lcms0  mntrRGB XYZ      acspMSFT    lcms                       -lcms                                               dmnd     jdesc     hdmdd     hwtpt  P   rXYZ  d   bXYZ  x   gXYZ     rTRC    gTRC  
  bTRC    chrm     $cprt     !desc       lcms generated                                                                                  desc       sRGB                                                                          
```

### `GET /rde/login/main-banner3.webp`
- **Full URL**: `https://images.staticcontents.net/rde/login/main-banner3.webp`
- **Status**: `200`
- **Content-Type**: `image/webp`
- **Saved Payload**: [`GET_images.staticcontents.net__rde_login_main-banner3.webp.txt`](./responses/GET_images.staticcontents.net__rde_login_main-banner3.webp.txt)

```json
RIFF WEBPVP8X
       { VP8 ܕ )	*|  %'w{~{_u<׾?5	'}u}OaO=%8Owߋ{a_=Qo~G@]
cGnEʳ}gU7/>U9E;~7޹~o?_{ʟ?o/~~ WkGܿ=gy__?iGo?߿/?~~['?/گ߿#gOM?_~D{w?|S <mKWW)޿;ۇ?Ao~g7s?cO߿WG5şZI͗wWw;? TAg_s/gk_u/ş?EC?lE'__~ _?SO??n-ۆ@q^tɅӺl2Kĺw-\`܉bWQKdŦICp\cz|FF9QU;lϳPZLaAv_+Kʥ^IMc¾mB|$jزeWD(H2s<u82:Lv5R`v8-ÿYd=-S׍"_lT	qKy:_.fi@LJgɦ}Ԙ{2a_CPjry+bKk~;Dh-pm3e">dq"G~jCGcֺ	{54*w"L~⍃K'
```

### `GET /rde/login/main-banner4.webp`
- **Full URL**: `https://images.staticcontents.net/rde/login/main-banner4.webp`
- **Status**: `200`
- **Content-Type**: `image/webp`
- **Saved Payload**: [`GET_images.staticcontents.net__rde_login_main-banner4.webp.txt`](./responses/GET_images.staticcontents.net__rde_login_main-banner4.webp.txt)

```json
RIFFt% WEBPVP8X
       { ALPHs?  mY	v]nh;kVmUT AeM@BJ8 YXP0!R1LF GG*l7!ش Q2(s84d!YQCl%ÒR3)k8$m0X H$L6BD1"]cO',gx`0BIũ_oF6P]sRf$I!eM@'/m3Ыy)FZ:N{c(Jײ5>O\|[~1_3cf'}%*XhD7p,ç39iS@M1zԖޭ\j ivz$E=%uU6Gb3]VS~Bh2F%efloi4ՓZ׍]z>)۪̀Gx*r"C93ľngt%kb6~FGɆȘ*3Q_̭&T-IM_q3(v(kmR0-p11nhH\[lyฅ":Zxw=zػAzv39fk<_95C4͟
"$)J_V<-E`oھnB(A]9!e^k*ͺ2֭]Ԥ0֯uID-	DUԟVZcg\%勰&0r,!Fώ_lef wJȹÿ̀!_5汞Q~RtĔ@*2W&:c>wK
```

### `GET /rde/login/main-banner5.webp`
- **Full URL**: `https://images.staticcontents.net/rde/login/main-banner5.webp`
- **Status**: `200`
- **Content-Type**: `image/webp`
- **Saved Payload**: [`GET_images.staticcontents.net__rde_login_main-banner5.webp.txt`](./responses/GET_images.staticcontents.net__rde_login_main-banner5.webp.txt)

```json
RIFF? WEBPVP8X
       { VP8  p+
*|   %^`EaGsOڼoAܟfz9UGΧqk(xz/~=\~/\?AoQZ_8(?q~oyOe{+c}+?^k;#?O򟺟?_S//G??#WU?/}B_O?qg/w?~ };@G0׸uO>P_?n=O_?W.7?/~}῾G?0}+O?uSyπ?;[qyG:wwOw??q'Gwۿu D,+CIbe|H̪{P=%1k/2H#3vb_N4 uhkM%͕!W*AXqEkoFjlz js]}/.1ﳡppx.
g8Px̟Ƈ\8Ky)q \7C'.z2Efh7!ˀ'( yxP6Lg=ǻ}&a8]M-7"24jZ#Lӝ֧DϪ0u*&LV鄋U7W
'l\W3e{[{/G
r)3dɳ}|md [ҝ~!c^ms\uZNr$EPNKj1D:$U8цߓ%릾@5p##~
```

### `GET /rde/login/pg-banner.webp`
- **Full URL**: `https://images.staticcontents.net/rde/login/pg-banner.webp`
- **Status**: `200`
- **Content-Type**: `image/webp`
- **Saved Payload**: [`GET_images.staticcontents.net__rde_login_pg-banner.webp.txt`](./responses/GET_images.staticcontents.net__rde_login_pg-banner.webp.txt)

```json
RIFF WEBPVP8X
      a   VP8   p*b    %T_3v^^Nxt}0=9@ _qEߑY/~|qaC/Oߓ=|Of?$<?/n} 0?~'s׿j?_JwkOOGϿW_C#_? ?{` ߠ_1C_Oh[/?~3/;'ُ#?C[[w~Wk[7aGO`~/?n??/Sﱟ?0}QgwK[M=?}Ke/o_r)Wy~D_UM%=AqP0P7VT4N7\/n+l!9mRe^{ Y;?[eU_7\S+FLQccU'1_w*Nݰk:b#HI&mT	Ht4x%]Eg4>tD0,O@,	9c<_Bdwm,Uki7Nbh֯ΔD!)\f/A<s>Q%} 6, 
O(JB8Bʰ貿^ʲק̞4&4&4&4&5
8)F3ػdoG"=x@-݋\h2lq[	U/*>_G% /-Rp%$T?a'03#oz@үxƊ)I)S}U쪛t`w֐
```

### `GET /splashpopup/splashpopuplist.json`
- **Full URL**: `https://images.staticcontents.net/splashpopup/splashpopuplist.json`
- **Status**: `200`
- **Content-Type**: `text/json`
- **Saved Payload**: [`GET_images.staticcontents.net__splashpopup_splashpopuplist.json.json`](./responses/GET_images.staticcontents.net__splashpopup_splashpopuplist.json.json)

```json
{
  "CLIENT": {
    "mediaType": "",
    "url": "",
    "redirecturl": "",
    "orientation": ""
  },
  "ADMIN": {
    "mediaType": "",
    "url": "",
    "redirecturl": "",
    "orientation": ""
  },
  "ADMINDESKTOP": {
    "mediaType": "",
    "url": "",
    "redirecturl": "",
    "orientation": ""
  },
  "CLIENTDESKTOP": {
    "mediaType": "",
    "url": "",
    "redirecturl": "",
    "orientation": ""
  }
}
```

### `POST /bets/user/open/event`
- **Full URL**: `https://report.radheex.com/bets/user/open/event`
- **Status**: `200`
- **Content-Type**: `application/json`
- **Saved Payload**: [`POST_report.radheex.com__bets_user_open_event.json`](./responses/POST_report.radheex.com__bets_user_open_event.json)

```json
{
  "items": [],
  "isSuccess": true
}
```

### `GET /maintenance`
- **Full URL**: `https://report.radheex.com/maintenance`
- **Status**: `200`
- **Content-Type**: `application/json`
- **Saved Payload**: [`GET_report.radheex.com__maintenance.json`](./responses/GET_report.radheex.com__maintenance.json)

```json
{
  "items": {
    "_id": "62fcda3b627070942400cb95",
    "createdAt": "2022-08-07 15:00:00",
    "isMaintenance": false,
    "from": "2026-08-24 20:00:00",
    "message": "System Maintenance Alert",
    "to": "2026-08-26 03:30:00",
    "type": "Maintenance"
  },
  "isSuccess": true
}
```

### `GET /static/js/main.dcbc770e.js`
- **Full URL**: `https://www.radheex.com/static/js/main.dcbc770e.js`
- **Status**: `200`
- **Content-Type**: `application/javascript`
- **Saved Payload**: [`GET_www.radheex.com__static_js_main.dcbc770e.js.txt`](./responses/GET_www.radheex.com__static_js_main.dcbc770e.js.txt)

```json
/*! For license information please see main.dcbc770e.js.LICENSE.txt */
!function(){var e={5354:function(e){e.exports=function(e,t){e.prototype=Object.create(t.prototype),e.prototype.constructor=e,e.__proto__=t}},5318:function(e){e.exports=function(e){return e&&e.__esModule?e:{default:e}}},1574:function(e,t,a){"use strict";var n={};a.r(n),a.d(n,{setHomeData:function(){return _n}});var r=a(7313),s=a(1168),o="radheex",i="com",l="dev"===window.location.host.split(".")[0].trim().toLowerCase(),c="repo
```

## 2. WebSocket Connections & Streaming

- **RECEIVED** (`wss://feed.radheex.com/socket.io/?token=eyJ0eXAiOiJKV1QiLCJhbGciOiJIUzI1NiJ9.eyJzdWIiOiJkZW1vY2xpZW50Iiwicm9sZSI6IkRlbW9DbGllbnQiLCJpc3MiOiJSREUiLCJleHAiOjE3OTM3NjM3MzYyODUsInB3ZGNoIjpmYWxzZSwiaXAiOiI0OS4zNi40My4xNzgifQ.DCmkmvu3jg7p2AUW1yP_XEsoEJSmWNXGxSWujU-lSug&cid=democlient_1793734938742&EIO=4&transport=websocket`): `0{"sid":"cJNzBtfL4NktUYU_TSv6","upgrades":[],"pingInterval":25000,"pingTimeout":20000,"maxPayload":1000000}`
- **SENT** (`wss://feed.radheex.com/socket.io/?token=eyJ0eXAiOiJKV1QiLCJhbGciOiJIUzI1NiJ9.eyJzdWIiOiJkZW1vY2xpZW50Iiwicm9sZSI6IkRlbW9DbGllbnQiLCJpc3MiOiJSREUiLCJleHAiOjE3OTM3NjM3MzYyODUsInB3ZGNoIjpmYWxzZSwiaXAiOiI0OS4zNi40My4xNzgifQ.DCmkmvu3jg7p2AUW1yP_XEsoEJSmWNXGxSWujU-lSug&cid=democlient_1793734938742&EIO=4&transport=websocket`): `40`
- **RECEIVED** (`wss://feed.radheex.com/socket.io/?token=eyJ0eXAiOiJKV1QiLCJhbGciOiJIUzI1NiJ9.eyJzdWIiOiJkZW1vY2xpZW50Iiwicm9sZSI6IkRlbW9DbGllbnQiLCJpc3MiOiJSREUiLCJleHAiOjE3OTM3NjM3MzYyODUsInB3ZGNoIjpmYWxzZSwiaXAiOiI0OS4zNi40My4xNzgifQ.DCmkmvu3jg7p2AUW1yP_XEsoEJSmWNXGxSWujU-lSug&cid=democlient_1793734938742&EIO=4&transport=websocket`): `40{"sid":"GHsBRgziL1AjQ2LwTSv7"}`
- **SENT** (`wss://feed.radheex.com/socket.io/?token=eyJ0eXAiOiJKV1QiLCJhbGciOiJIUzI1NiJ9.eyJzdWIiOiJkZW1vY2xpZW50Iiwicm9sZSI6IkRlbW9DbGllbnQiLCJpc3MiOiJSREUiLCJleHAiOjE3OTM3NjM3MzYyODUsInB3ZGNoIjpmYWxzZSwiaXAiOiI0OS4zNi40My4xNzgifQ.DCmkmvu3jg7p2AUW1yP_XEsoEJSmWNXGxSWujU-lSug&cid=democlient_1793734938742&EIO=4&transport=websocket`): `42["market_room","1.264908909"]`
- **SENT** (`wss://feed.radheex.com/socket.io/?token=eyJ0eXAiOiJKV1QiLCJhbGciOiJIUzI1NiJ9.eyJzdWIiOiJkZW1vY2xpZW50Iiwicm9sZSI6IkRlbW9DbGllbnQiLCJpc3MiOiJSREUiLCJleHAiOjE3OTM3NjM3MzYyODUsInB3ZGNoIjpmYWxzZSwiaXAiOiI0OS4zNi40My4xNzgifQ.DCmkmvu3jg7p2AUW1yP_XEsoEJSmWNXGxSWujU-lSug&cid=democlient_1793734938742&EIO=4&transport=websocket`): `42["market_room","43907183"]`
- **SENT** (`wss://feed.radheex.com/socket.io/?token=eyJ0eXAiOiJKV1QiLCJhbGciOiJIUzI1NiJ9.eyJzdWIiOiJkZW1vY2xpZW50Iiwicm9sZSI6IkRlbW9DbGllbnQiLCJpc3MiOiJSREUiLCJleHAiOjE3OTM3NjM3MzYyODUsInB3ZGNoIjpmYWxzZSwiaXAiOiI0OS4zNi40My4xNzgifQ.DCmkmvu3jg7p2AUW1yP_XEsoEJSmWNXGxSWujU-lSug&cid=democlient_1793734938742&EIO=4&transport=websocket`): `42["market_room","43909778"]`
- **SENT** (`wss://feed.radheex.com/socket.io/?token=eyJ0eXAiOiJKV1QiLCJhbGciOiJIUzI1NiJ9.eyJzdWIiOiJkZW1vY2xpZW50Iiwicm9sZSI6IkRlbW9DbGllbnQiLCJpc3MiOiJSREUiLCJleHAiOjE3OTM3NjM3MzYyODUsInB3ZGNoIjpmYWxzZSwiaXAiOiI0OS4zNi40My4xNzgifQ.DCmkmvu3jg7p2AUW1yP_XEsoEJSmWNXGxSWujU-lSug&cid=democlient_1793734938742&EIO=4&transport=websocket`): `42["market_room","43909779"]`
- **SENT** (`wss://feed.radheex.com/socket.io/?token=eyJ0eXAiOiJKV1QiLCJhbGciOiJIUzI1NiJ9.eyJzdWIiOiJkZW1vY2xpZW50Iiwicm9sZSI6IkRlbW9DbGllbnQiLCJpc3MiOiJSREUiLCJleHAiOjE3OTM3NjM3MzYyODUsInB3ZGNoIjpmYWxzZSwiaXAiOiI0OS4zNi40My4xNzgifQ.DCmkmvu3jg7p2AUW1yP_XEsoEJSmWNXGxSWujU-lSug&cid=democlient_1793734938742&EIO=4&transport=websocket`): `42["market_room","1.264920351"]`
- **SENT** (`wss://feed.radheex.com/socket.io/?token=eyJ0eXAiOiJKV1QiLCJhbGciOiJIUzI1NiJ9.eyJzdWIiOiJkZW1vY2xpZW50Iiwicm9sZSI6IkRlbW9DbGllbnQiLCJpc3MiOiJSREUiLCJleHAiOjE3OTM3NjM3MzYyODUsInB3ZGNoIjpmYWxzZSwiaXAiOiI0OS4zNi40My4xNzgifQ.DCmkmvu3jg7p2AUW1yP_XEsoEJSmWNXGxSWujU-lSug&cid=democlient_1793734938742&EIO=4&transport=websocket`): `42["market_room","1.264742339"]`
- **SENT** (`wss://feed.radheex.com/socket.io/?token=eyJ0eXAiOiJKV1QiLCJhbGciOiJIUzI1NiJ9.eyJzdWIiOiJkZW1vY2xpZW50Iiwicm9sZSI6IkRlbW9DbGllbnQiLCJpc3MiOiJSREUiLCJleHAiOjE3OTM3NjM3MzYyODUsInB3ZGNoIjpmYWxzZSwiaXAiOiI0OS4zNi40My4xNzgifQ.DCmkmvu3jg7p2AUW1yP_XEsoEJSmWNXGxSWujU-lSug&cid=democlient_1793734938742&EIO=4&transport=websocket`): `42["market_room","1.264742472"]`
- **SENT** (`wss://feed.radheex.com/socket.io/?token=eyJ0eXAiOiJKV1QiLCJhbGciOiJIUzI1NiJ9.eyJzdWIiOiJkZW1vY2xpZW50Iiwicm9sZSI6IkRlbW9DbGllbnQiLCJpc3MiOiJSREUiLCJleHAiOjE3OTM3NjM3MzYyODUsInB3ZGNoIjpmYWxzZSwiaXAiOiI0OS4zNi40My4xNzgifQ.DCmkmvu3jg7p2AUW1yP_XEsoEJSmWNXGxSWujU-lSug&cid=democlient_1793734938742&EIO=4&transport=websocket`): `42["market_room","1.264742583"]`
- **SENT** (`wss://feed.radheex.com/socket.io/?token=eyJ0eXAiOiJKV1QiLCJhbGciOiJIUzI1NiJ9.eyJzdWIiOiJkZW1vY2xpZW50Iiwicm9sZSI6IkRlbW9DbGllbnQiLCJpc3MiOiJSREUiLCJleHAiOjE3OTM3NjM3MzYyODUsInB3ZGNoIjpmYWxzZSwiaXAiOiI0OS4zNi40My4xNzgifQ.DCmkmvu3jg7p2AUW1yP_XEsoEJSmWNXGxSWujU-lSug&cid=democlient_1793734938742&EIO=4&transport=websocket`): `42["market_room","1.264742695"]`
- **SENT** (`wss://feed.radheex.com/socket.io/?token=eyJ0eXAiOiJKV1QiLCJhbGciOiJIUzI1NiJ9.eyJzdWIiOiJkZW1vY2xpZW50Iiwicm9sZSI6IkRlbW9DbGllbnQiLCJpc3MiOiJSREUiLCJleHAiOjE3OTM3NjM3MzYyODUsInB3ZGNoIjpmYWxzZSwiaXAiOiI0OS4zNi40My4xNzgifQ.DCmkmvu3jg7p2AUW1yP_XEsoEJSmWNXGxSWujU-lSug&cid=democlient_1793734938742&EIO=4&transport=websocket`): `42["market_room","1.264742827"]`
- **SENT** (`wss://feed.radheex.com/socket.io/?token=eyJ0eXAiOiJKV1QiLCJhbGciOiJIUzI1NiJ9.eyJzdWIiOiJkZW1vY2xpZW50Iiwicm9sZSI6IkRlbW9DbGllbnQiLCJpc3MiOiJSREUiLCJleHAiOjE3OTM3NjM3MzYyODUsInB3ZGNoIjpmYWxzZSwiaXAiOiI0OS4zNi40My4xNzgifQ.DCmkmvu3jg7p2AUW1yP_XEsoEJSmWNXGxSWujU-lSug&cid=democlient_1793734938742&EIO=4&transport=websocket`): `42["market_room","1.264842870"]`
- **SENT** (`wss://feed.radheex.com/socket.io/?token=eyJ0eXAiOiJKV1QiLCJhbGciOiJIUzI1NiJ9.eyJzdWIiOiJkZW1vY2xpZW50Iiwicm9sZSI6IkRlbW9DbGllbnQiLCJpc3MiOiJSREUiLCJleHAiOjE3OTM3NjM3MzYyODUsInB3ZGNoIjpmYWxzZSwiaXAiOiI0OS4zNi40My4xNzgifQ.DCmkmvu3jg7p2AUW1yP_XEsoEJSmWNXGxSWujU-lSug&cid=democlient_1793734938742&EIO=4&transport=websocket`): `42["market_room","1.264845945"]`

## 3. Discovered Assets Summary
- **Images**: 113 URLs
- **SVGs**: 0 URLs
- **Fonts**: 4 URLs
- **Scripts**: 2 URLs
- **Stylesheets**: 5 URLs
