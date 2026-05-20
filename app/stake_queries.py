# Auto-generated from queries.js — production GraphQL queries used by Stake.com web.
# Diambil dari DevTools Network tab (Copy as fetch), termasuk semua fragment.

QUERY_SPORT_INDEX = r'''
  query SportIndex($sport: String!, $group: String!, $type: SportSearchEnum = popular) {
    slugSport(sport: $sport) {
      id
      name
      templates(group: $group) {
        id
        name
        extId
      }
      categoryList(type: $type, limit: 100) {
        id
        slug
        name
        countryCode
        fixtureCount(type: $type)
        tournamentList(type: $type, limit: 100) {
          id
          slug
          name
          fixtureCount(type: $type)
          category {
            id
            slug
            name
            countryCode
          }
          fixtureList(type: $type, limit: 50) {
            ...FixturePreview
            ...UfcFrontRowSeat
            groups(groups: [$group], status: [active, suspended, deactivated]) {
              ...SportGroupTemplates
            }
          }
        }
      }
    }
  }

  fragment FixturePreview on SportFixture {
    id
    ...SportFixtureLiveStreamExists
    ...FixtureOptionsSameGameMultiButton_SportFixture
    status
    slug
    name
    provider
    marketCount(status: [active, suspended])
    extId
    liveWidgetUrl
    widgetUrl
    data {
      __typename
      ...SportFixtureDataMatch
      ...SportFixtureDataOutright
    }
    tournament {
      ...TournamentTreeNested
    }
    eventStatus {
      ...SportFixtureEventStatus
      ...EsportFixtureEventStatus
    }
  }

  fragment SportFixtureLiveStreamExists on SportFixture {
    id
    betradarStream { exists }
    imgArenaStream { exists }
    abiosStream {
      exists
      stream { startTime id }
    }
    geniussportsStream(deliveryType: hls) { exists }
    statsPerformStream(getData: false) { isAvailable geoBlocked }
    liveStream { data { isAvailable } }
  }

  fragment FixtureOptionsSameGameMultiButton_SportFixture on SportFixture {
    sgmAvailable: customBetAvailable
    swish: swishGame {
      sport: swishSport {
        sgmAvailable: customBetAvailable
        sgmLiveAvailable: liveCustomBetAvailable
      }
    }
  }

  fragment SportFixtureDataMatch on SportFixtureDataMatch {
    startTime
    competitors { ...SportFixtureCompetitor }
    teams { name qualifier }
    tvChannels { language name streamUrl }
    __typename
  }

  fragment SportFixtureCompetitor on SportFixtureCompetitor {
    name
    defaultName
    extId
    countryCode
    abbreviation
    iconPath
  }

  fragment SportFixtureDataOutright on SportFixtureDataOutright {
    name
    startTime
    endTime
    __typename
  }

  fragment TournamentTreeNested on SportTournament {
    id
    name
    slug
    category {
      ...CategoryTreeNested
      cashoutEnabled
    }
  }

  fragment CategoryTreeNested on SportCategory {
    id
    name
    slug
    sport { id name slug }
  }

  fragment SportFixtureEventStatus on SportFixtureEventStatusData {
    __typename
    homeScore
    awayScore
    matchStatus
    clock { matchTime remainingTime }
    periodScores { homeScore awayScore matchStatus }
    currentTeamServing
    homeGameScore
    awayGameScore
    statistic {
      yellowCards { away home }
      redCards { away home }
      corners { home away }
    }
  }

  fragment EsportFixtureEventStatus on EsportFixtureEventStatus {
    matchStatus
    homeScore
    awayScore
    scoreboard {
      homeGold awayGold homeGoals awayGoals homeKills awayKills
      gameTime homeDestroyedTowers awayDestroyedTurrets
      currentRound currentCtTeam currentDefTeam time
      awayWonRounds homeWonRounds remainingGameTime
    }
    periodScores {
      type number
      awayGoals awayKills awayScore
      homeGoals homeKills homeScore
      awayWonRounds homeWonRounds matchStatus
    }
    __typename
  }

  fragment UfcFrontRowSeat on SportFixture {
    frontRowSeatFight { fightId }
    tournament { frontRowSeatEvent { identifier } }
  }

  fragment SportGroupTemplates on SportGroup {
    ...SportGroup
    templates(limit: 10, includeEmpty: true) {
      ...SportGroupTemplate
      markets(limit: 1) {
        ...SportMarket
        outcomes { ...SportMarketOutcome }
      }
    }
  }

  fragment SportGroup on SportGroup {
    name
    translation
    rank
  }

  fragment SportGroupTemplate on SportGroupTemplate {
    extId
    rank
    name
  }

  fragment SportMarket on SportMarket {
    id
    name
    status
    extId
    specifiers
    customBetAvailable
    provider
  }

  fragment SportMarketOutcome on SportMarketOutcome {
    __typename
    id
    active
    odds
    name
    customBetAvailable
  }
'''

QUERY_FIXTURE_DETAIL = r'''
query FixturePage_SlugFixture($fixture: String!, $groups: [String!]!) {
  slugFixture(fixture: $fixture) {
    id
    name
    slug
    customBetAvailable
    liveWidgetUrl
    widgetUrl
    ...FixtureWidget_SportFixture
    ...CustomSwishBetStickyHeader_SportFixture
    ...CustomSportBetStickyHeader_SportFixture
    ...TemplateMarket_SportFixture
    ...SportFixtureScoreboard_SportFixture
    ...SwishMarket_SportFixture
    ...SportFixtureTabs_SportFixture
    ...FixtureOptionsSameGameMultiButton_SportFixture
    contentNotes {
      ...FixtureNotice_ContentNote
    }
    tournament {
      id
      name
      slug
      category {
        id
        name
        slug
        sport {
          id
          name
          slug
          allGroups {
            ...SportGroup
            templates(includeEmpty: true, limit: 1) {
              id
            }
          }
          contentNotes {
            ...FixtureNotice_ContentNote
          }
        }
        contentNotes {
          ...FixtureNotice_ContentNote
        }
      }
      contentNotes {
        ...FixtureNotice_ContentNote
      }
    }
    maps: groups(groups: ["maps"]) {
      id
      ...SportGroup
      templates(includeEmpty: false) {
        id
        extId
        markets {
          status
          specifiers
          extId
        }
      }
    }
    group: groups(groups: $groups) {
      ...SportGroup
      templates(includeEmpty: false) {
        id
        ...SportGroupTemplate
        markets {
          ...SportMarket
          outcomes {
            ...SportMarketOutcome
            extId
          }
        }
      }
    }
    groups {
      name
      translation
    }
    data {
      __typename
    }
  }
}

fragment FixtureWidget_SportFixture on SportFixture {
  id
  extId
  provider
  tournament {
    category {
      sport {
        slug
      }
    }
    frontRowSeatEvent {
      identifier
    }
  }
  frontRowSeatFight {
    fightId
  }
}

fragment CustomSwishBetStickyHeader_SportFixture on SportFixture {
  id
  tournament {
    slug
    category {
      sport {
        slug
      }
    }
  }
  swishGame {
    swishSportId
    status
  }
}

fragment CustomSportBetStickyHeader_SportFixture on SportFixture {
  id
  status
  provider
  tournament {
    category {
      sport {
        slug
      }
    }
  }
}

fragment TemplateMarket_SportFixture on SportFixture {
  ...Default_SportFixture
  ...DefaultEsport_SportFixture
  ...BracketValue_SportFixture
  ...CompetitorName_SportFixture
  ...CorrectScore_SportFixture
  ...CustomMarketSelect_SportFixture
  ...CustomMarketTable_SportFixture
  ...GameSetCorrectScoreOrBreak_SportFixture
  ...HalfTimeFullTimeCorrectScore_SportFixture
  ...LastValue_SportFixture
  ...Players_SportFixture
  ...ShortestOdds_SportFixture
  ...Table_SportFixture
  ...TwoColumns_SportFixture
  ...OddinTeamMarket_SportFixture
  ...OddinTeamDoubleMarket_SportFixture
  ...OddinMarginMarket_SportFixture
  groups {
    rank
    templates {
      ...Default_SportGroupTemplate
      ...DefaultEsport_SportGroupTemplate
      ...BracketValue_SportGroupTemplate
      ...CompetitorName_SportGroupTemplate
      ...CorrectScore_SportGroupTemplate
      ...CustomMarketSelect_SportGroupTemplate
      ...CustomMarketTable_SportGroupTemplate
      ...GameSetCorrectScoreOrBreak_SportGroupTemplate
      ...HalfTimeFullTimeCorrectScore_SportGroupTemplate
      ...LastValue_SportGroupTemplate
      ...Players_SportGroupTemplate
      ...ShortestOdds_SportGroupTemplate
    }
  }
}

fragment Default_SportFixture on SportFixture {
  ...SportBetOutcome_SportFixture
  ...CustomSportBetOutcome_SportFixture
  data {
    ... on SportFixtureDataMatch {
      teams {
        qualifier
        name
      }
    }
  }
}

fragment SportBetOutcome_SportFixture on SportFixture {
  id
  status
  provider
  tournament {
    category {
      sport {
        slug
      }
    }
  }
  data {
    ... on SportFixtureDataMatch {
      competitors {
        name
        abbreviation
      }
      startTime
    }
    ... on SportFixtureDataOutright {
      name
      startTime
    }
  }
}

fragment CustomSportBetOutcome_SportFixture on SportFixture {
  id
  status
  provider
  data {
    ... on SportFixtureDataMatch {
      competitors {
        name
        abbreviation
      }
      startTime
    }
    ... on SportFixtureDataOutright {
      name
      startTime
    }
  }
}

fragment DefaultEsport_SportFixture on SportFixture {
  ...SportBetOutcome_SportFixture
  ...CustomSportBetOutcome_SportFixture
  data {
    ... on SportFixtureDataMatch {
      teams {
        qualifier
        name
      }
    }
  }
}

fragment BracketValue_SportFixture on SportFixture {
  ...CustomMarketTable_SportFixture
  ...Table_SportFixture
}

fragment CustomMarketTable_SportFixture on SportFixture {
  ...SportBetOutcome_SportFixture
  ...CustomSportBetOutcome_SportFixture
  status
}

fragment Table_SportFixture on SportFixture {
  ...SportBetOutcome_SportFixture
  ...CustomSportBetOutcome_SportFixture
}

fragment CompetitorName_SportFixture on SportFixture {
  ...CustomMarketTable_SportFixture
  ...Table_SportFixture
}

fragment CorrectScore_SportFixture on SportFixture {
  ...SportBetOutcome_SportFixture
  ...CustomSportBetOutcome_SportFixture
  ...CustomMarketTable_SportFixture
  id
}

fragment CustomMarketSelect_SportFixture on SportFixture {
  ...SportBetOutcome_SportFixture
  ...CustomSportBetOutcome_SportFixture
  ...CustomMarketTable_SportFixture
  id
}

fragment GameSetCorrectScoreOrBreak_SportFixture on SportFixture {
  ...CustomMarketTable_SportFixture
  ...Table_SportFixture
}

fragment HalfTimeFullTimeCorrectScore_SportFixture on SportFixture {
  ...SportBetOutcome_SportFixture
  ...CustomSportBetOutcome_SportFixture
  ...CustomMarketTable_SportFixture
  id
  data {
    ... on SportFixtureDataMatch {
      competitors {
        name
      }
    }
  }
}

fragment LastValue_SportFixture on SportFixture {
  ...CustomMarketTable_SportFixture
  ...Table_SportFixture
}

fragment Players_SportFixture on SportFixture {
  ...SportBetOutcome_SportFixture
  ...CustomSportBetOutcome_SportFixture
}

fragment ShortestOdds_SportFixture on SportFixture {
  ...Default_SportFixture
}

fragment TwoColumns_SportFixture on SportFixture {
  ...SportBetOutcome_SportFixture
  ...CustomSportBetOutcome_SportFixture
}

fragment OddinTeamMarket_SportFixture on SportFixture {
  ...TwoColumns_SportFixture
  data {
    ... on SportFixtureDataMatch {
      teams {
        name
        qualifier
      }
    }
  }
}

fragment OddinTeamDoubleMarket_SportFixture on SportFixture {
  ...TwoColumns_SportFixture
}

fragment OddinMarginMarket_SportFixture on SportFixture {
  ...TwoColumns_SportFixture
  data {
    ... on SportFixtureDataMatch {
      teams {
        name
        qualifier
      }
    }
  }
}

fragment Default_SportGroupTemplate on SportGroupTemplate {
  extId
  markets {
    ...SportBetOutcome_SportMarket
    ...CustomSportBetOutcome_SportMarket
    id
    outcomes {
      id
      ...SportBetOutcome_SportMarketOutcome
      ...CustomSportBetOutcome_SportMarketOutcome
    }
  }
}

fragment SportBetOutcome_SportMarket on SportMarket {
  id
  extId
  name
  status
  specifiers
  customBetAvailable
  provider
}

fragment CustomSportBetOutcome_SportMarket on SportMarket {
  id
  extId
  name
  status
  specifiers
  customBetAvailable
  provider
}

fragment SportBetOutcome_SportMarketOutcome on SportMarketOutcome {
  id
  active
  odds
  name
  customBetAvailable
}

fragment CustomSportBetOutcome_SportMarketOutcome on SportMarketOutcome {
  id
  active
  odds
  name
  customBetAvailable
}

fragment DefaultEsport_SportGroupTemplate on SportGroupTemplate {
  extId
  markets {
    ...SportBetOutcome_SportMarket
    ...CustomSportBetOutcome_SportMarket
    id
    name
    outcomes {
      id
      name
      ...SportBetOutcome_SportMarketOutcome
      ...CustomSportBetOutcome_SportMarketOutcome
    }
  }
}

fragment BracketValue_SportGroupTemplate on SportGroupTemplate {
  id
  name
  ...CustomMarketTable_SportGroupTemplate
}

fragment CustomMarketTable_SportGroupTemplate on SportGroupTemplate {
  extId
  markets {
    ...SportBetOutcome_SportMarket
    ...CustomSportBetOutcome_SportMarket
    id
    name
    provider
    outcomes {
      id
      ...SportBetOutcome_SportMarketOutcome
      ...CustomSportBetOutcome_SportMarketOutcome
      extId
    }
  }
}

fragment CompetitorName_SportGroupTemplate on SportGroupTemplate {
  id
  name
  ...CustomMarketTable_SportGroupTemplate
}

fragment CorrectScore_SportGroupTemplate on SportGroupTemplate {
  ...CustomMarketTable_SportGroupTemplate
  markets {
    ...SportBetOutcome_SportMarket
    ...CustomSportBetOutcome_SportMarket
    id
    status
    outcomes {
      ...SportBetOutcome_SportMarketOutcome
      ...CustomSportBetOutcome_SportMarketOutcome
      active
      id
      odds
      name
      customBetAvailable
    }
  }
}

fragment CustomMarketSelect_SportGroupTemplate on SportGroupTemplate {
  ...CustomMarketTable_SportGroupTemplate
  markets {
    ...SportBetOutcome_SportMarket
    ...CustomSportBetOutcome_SportMarket
    id
    status
    outcomes {
      ...SportBetOutcome_SportMarketOutcome
      ...CustomSportBetOutcome_SportMarketOutcome
      active
      id
      odds
      name
      customBetAvailable
    }
  }
}

fragment GameSetCorrectScoreOrBreak_SportGroupTemplate on SportGroupTemplate {
  ...CustomMarketTable_SportGroupTemplate
}

fragment HalfTimeFullTimeCorrectScore_SportGroupTemplate on SportGroupTemplate {
  ...CustomMarketTable_SportGroupTemplate
  extId
  markets {
    ...SportBetOutcome_SportMarket
    ...CustomSportBetOutcome_SportMarket
    id
    status
    outcomes {
      id
      active
      odds
      name
      customBetAvailable
      ...SportBetOutcome_SportMarketOutcome
      ...CustomSportBetOutcome_SportMarketOutcome
    }
  }
}

fragment LastValue_SportGroupTemplate on SportGroupTemplate {
  id
  name
  ...CustomMarketTable_SportGroupTemplate
}

fragment Players_SportGroupTemplate on SportGroupTemplate {
  name
  markets {
    ...SportBetOutcome_SportMarket
    ...CustomSportBetOutcome_SportMarket
    id
    name
    outcomes {
      id
      ...SportBetOutcome_SportMarketOutcome
      ...CustomSportBetOutcome_SportMarketOutcome
    }
  }
}

fragment ShortestOdds_SportGroupTemplate on SportGroupTemplate {
  ...Default_SportGroupTemplate
}

fragment SportFixtureScoreboard_SportFixture on SportFixture {
  ...Livestream_SportFixture
  ...FixtureWidget_SportFixture
  ...MatchStatistics_SportFixture
  betradarStream {
    exists
  }
  imgArenaStream {
    exists
  }
  abiosStream {
    exists
  }
  geniussportsStream(deliveryType: hls) {
    exists
  }
  statsPerformStream(getData: false) {
    isAvailable
    geoBlocked
  }
  liveStream {
    data {
      isAvailable
    }
  }
  data {
    ... on SportFixtureDataMatch {
      tvChannels {
        name
        language
        streamUrl
      }
    }
  }
}

fragment Livestream_SportFixture on SportFixture {
  id
  slug
  tournament {
    slug
    category {
      slug
      sport {
        slug
      }
    }
  }
  data {
    ... on SportFixtureDataMatch {
      tvChannels {
        name
        language
        streamUrl
      }
    }
  }
}

fragment MatchStatistics_SportFixture on SportFixture {
  extId
  status
  provider
  eventStatus {
    __typename
    ... on SportFixtureEventStatusData {
      matchStatus
      statistic {
        corners {
          away
          home
        }
        redCards {
          away
          home
        }
        yellowCards {
          away
          home
        }
      }
      homeScore
      awayScore
      homeGameScore
      awayGameScore
      currentTeamServing
      periodScores {
        matchStatus
        homeScore
        homeGoals
        homeKills
        homeWonRounds
        awayScore
        awayGoals
        awayKills
        awayWonRounds
      }
      clock {
        matchTime
        remainingTime
      }
    }
    ... on EsportFixtureEventStatus {
      matchStatus
      homeScore
      awayScore
      scoreboard {
        gameTime
        remainingGameTime
        homeKills
        homeWonRounds
        awayKills
        awayWonRounds
      }
      periodScores {
        matchStatus
        homeScore
        homeGoals
        homeKills
        homeWonRounds
        awayScore
        awayGoals
        awayKills
        awayWonRounds
      }
    }
  }
  tournament {
    slug
    category {
      slug
    }
  }
  data {
    ... on SportFixtureDataMatch {
      startTime
      tvChannels {
        name
        streamUrl
        language
      }
      teams {
        name
        qualifier
      }
      competitors {
        extId
        name
        defaultName
        abbreviation
        iconPath
        countryCode
      }
    }
    ... on SportFixtureDataOutright {
      startTime
      name
    }
  }
}

fragment SwishMarket_SportFixture on SportFixture {
  swishGame {
    id
    status
    customBetEnabled
  }
}

fragment SportFixtureTabs_SportFixture on SportFixture {
  ...Preview_SportFixture
  ...SwishMarket_SportFixture
  maps: groups(groups: ["maps"]) {
    id
    ...SportGroup
    templates(includeEmpty: false) {
      id
      extId
      markets {
        status
        specifiers
        extId
      }
    }
  }
  groups {
    name
    rank
  }
}

fragment Preview_SportFixture on SportFixture {
  ...Frame_SportFixture
  ...Market_SportFixture
  id
  provider
  status
  slug
  marketCount(status: [active, suspended])
  ...FixtureOptionsSameGameMultiButton_SportFixture
  tournament {
    slug
    category {
      slug
      sport {
        slug
      }
    }
  }
  data {
    ... on SportFixtureDataMatch {
      competitors {
        name
      }
    }
  }
}

fragment Frame_SportFixture on SportFixture {
  ...FixtureMatchScore_SportFixture
  ...FixtureOptionsOddin_SportFixture
  ...FixtureOptionsBetRadar_SportFixture
  ...FixtureStatus_SportFixture
  ...FixtureOptionsSameGameMultiButton_SportFixture
  name
  slug
  eventStatus {
    __typename
    ... on SportFixtureEventStatusData {
      currentTeamServing
    }
  }
  marketCount(status: [active, suspended])
  data {
    ... on SportFixtureDataMatch {
      __typename
      competitors {
        name
        defaultName
        extId
        iconPath
        countryCode
      }
      teams {
        name
      }
    }
  }
  tournament {
    id
    name
    slug
    category {
      id
      name
      slug
      sport {
        id
        name
        slug
      }
    }
  }
}

fragment FixtureMatchScore_SportFixture on SportFixture {
  status
  tournament {
    category {
      sport {
        slug
      }
    }
  }
  eventStatus {
    ... on SportFixtureEventStatusData {
      homeScore
      awayScore
      matchStatus
      homeGameScore
      awayGameScore
      periodScores {
        homeScore
        awayScore
      }
    }
    ... on EsportFixtureEventStatus {
      homeScore
      awayScore
      periodScores {
        homeScore
        awayScore
      }
      scoreboard {
        homeKills
        homeWonRounds
        awayKills
        awayWonRounds
      }
    }
  }
}

fragment FixtureOptionsOddin_SportFixture on SportFixture {
  id
  extId
  name
  provider
  status
  widgetUrl
  liveWidgetUrl
  imgArenaStream {
    exists
  }
  geniussportsStream(deliveryType: hls) {
    exists
  }
  betradarStream {
    exists
  }
  tournament {
    slug
    frontRowSeatEvent {
      identifier
    }
    category {
      slug
      sport {
        slug
      }
    }
  }
  data {
    ... on SportFixtureDataMatch {
      competitors {
        name
        abbreviation
      }
      tvChannels {
        name
        streamUrl
        language
      }
      startTime
    }
    ... on SportFixtureDataOutright {
      name
      startTime
    }
  }
}

fragment FixtureOptionsBetRadar_SportFixture on SportFixture {
  id
  extId
  name
  provider
  status
  widgetUrl
  liveWidgetUrl
  imgArenaStream {
    exists
  }
  geniussportsStream(deliveryType: hls) {
    exists
  }
  betradarStream {
    exists
  }
  statsPerformStream(getData: false) {
    isAvailable
    geoBlocked
  }
  liveStream {
    data {
      isAvailable
    }
  }
  frontRowSeatFight {
    fightId
  }
  tournament {
    slug
    frontRowSeatEvent {
      identifier
    }
    category {
      slug
      sport {
        slug
      }
    }
  }
  data {
    ... on SportFixtureDataMatch {
      competitors {
        name
        abbreviation
      }
      tvChannels {
        name
        streamUrl
        language
      }
      startTime
    }
    ... on SportFixtureDataOutright {
      name
      startTime
    }
  }
}

fragment FixtureStatus_SportFixture on SportFixture {
  id
  status
  ...FixtureOptions_SportFixture
  ...Live_SportFixture
  ...Active_SportFixture
}

fragment FixtureOptions_SportFixture on SportFixture {
  ...FixtureOptionsOddin_SportFixture
  ...FixtureOptionsBetRadar_SportFixture
}

fragment Live_SportFixture on SportFixture {
  ...FixtureScore_SportFixture
  provider
  eventStatus {
    ... on SportFixtureEventStatusData {
      matchStatus
      periodScores {
        matchStatus
      }
      clock {
        matchTime
        remainingTime
      }
    }
    ... on EsportFixtureEventStatus {
      matchStatus
      periodScores {
        matchStatus
      }
      scoreboard {
        gameTime
        remainingGameTime
      }
    }
  }
  tournament {
    category {
      sport {
        slug
      }
    }
  }
}

fragment FixtureScore_SportFixture on SportFixture {
  provider
  eventStatus {
    ... on SportFixtureEventStatusData {
      homeScore
      awayScore
      matchStatus
      periodScores {
        homeScore
        awayScore
      }
    }
    ... on EsportFixtureEventStatus {
      homeScore
      awayScore
      periodScores {
        homeScore
        awayScore
      }
      scoreboard {
        homeKills
        homeWonRounds
        awayKills
        awayWonRounds
      }
    }
  }
  tournament {
    category {
      sport {
        slug
      }
    }
  }
}

fragment Active_SportFixture on SportFixture {
  data {
    ... on SportFixtureDataOutright {
      endTime
    }
    ... on SportFixtureDataMatch {
      startTime
    }
  }
}

fragment FixtureOptionsSameGameMultiButton_SportFixture on SportFixture {
  sgmAvailable: customBetAvailable
  swish: swishGame {
    sport: swishSport {
      sgmAvailable: customBetAvailable
      sgmLiveAvailable: liveCustomBetAvailable
    }
  }
}

fragment Market_SportFixture on SportFixture {
  ...SportBetOutcome_SportFixture
  id
  status
  data {
    ... on SportFixtureDataMatch {
      teams {
        name
        qualifier
      }
      competitors {
        name
        abbreviation
      }
    }
  }
}

fragment SportGroup on SportGroup {
  name
  translation
  rank
}

fragment FixtureNotice_ContentNote on ContentNote {
  id
  linkText
  linkUrl
  message
}

fragment SportGroupTemplate on SportGroupTemplate {
  extId
  rank
  name
}

fragment SportMarket on SportMarket {
  id
  name
  status
  extId
  specifiers
  customBetAvailable
  provider
}

fragment SportMarketOutcome on SportMarketOutcome {
  __typename
  id
  active
  odds
  name
  customBetAvailable
}'''
