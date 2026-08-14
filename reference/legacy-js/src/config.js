export const DEFAULT_SCENARIO = {
  seed: 20260813,
  aircraft: { type: 'A320_180', rows: 30, seatsPerRow: 6, loadFactor: 1.0 },
  flightContext: {
    delayMinutes: 20,
    priorDelayUpdates: 1,
    priorGateWaitMinutes: 35,
    priorAirportDwellMinutes: 100,
    connectionPressureShare: 0.12
  },
  population: {
    familyPassengerShare: 0.30,
    handLuggageShare: 0.75,
    twoBagShareAmongBagPassengers: 0.08
  },
  preparation: {
    readinessTarget: 0.90,
    firstCohortTarget: 0.95,
    gateUsableAreaM2: 190,
    averageStartDistanceM: 12,
    maxPreparationSeconds: 1800,
    strictPreparation: true
  },
  access: {
    mode: 'bridge',
    bridgeLengthM: 35,
    bridgeWalkSpeedMps: 1.15,
    gateScanMeanSeconds: 2.4,
    bridgeMinimumHeadwaySeconds: 3.7,
    busCount: 2,
    busCapacity: 90,
    busBoardMeanSeconds: 1.8,
    busTravelMeanSeconds: 180,
    busTravelSdSeconds: 25,
    busUnloadMeanSeconds: 1.25
  },
  boarding: {
    strategy: 'random_front',
    serviceModel: 'field_calibrated',
    cellSizeM: 0.4,
    dtSeconds: 0.5,
    aisleCellsPerRow: 2,
    walkingSpeedMps: 0.8,
    baggageWeibullShape: 1.7,
    baggageWeibullScaleSeconds: 16.0,
    seatMovementTriangularSeconds: [1.8, 2.4, 3.0],
    customSeatBaseSeconds: 15,
    customLoadThreshold: 0.60,
    customIncrementSeconds: 5,
    customIncrementLoadStep: 0.10,
    maxBoardingSeconds: 3600
  }
};

// These coefficients are intentionally isolated because they are NOT calibrated for normal gate boarding.
// They make the state model coherent and testable, but must be estimated from observation/survey data.
export const PROVISIONAL_BEHAVIOUR = {
  frustrationSlope: 0.12,
  initial: {
    delay: 0.26,
    priorGateWait: 0.10,
    airportDwell: 0.05,
    uncertainty: 0.16,
    fatigue: 0.17,
    connection: 0.18,
    unreliableInformation: 0.14
  },
  preparationPerMinute: {
    uncertainty: 0.055,
    noProgress: 0.050,
    crowding: 0.070,
    instruction: 0.055,
    correctionShock: 0.090,
    visibleProgressRecovery: 0.060,
    seatedRecovery: 0.025,
    socialCoupling: 0.018
  },
  transferPerMinute: {
    bridgeWaiting: 0.050,
    bridgeWalkingRecovery: 0.045,
    busWaiting: 0.065,
    busCrowding: 0.050,
    busMovingRecovery: 0.020,
    unloadingRecovery: 0.050
  },
  cabinPerMinute: {
    doorQueue: 0.050,
    aisleBlocked: 0.085,
    aisleMovingRecovery: 0.050,
    rowServiceEffort: 0.025
  },
  decision: {
    activationBase: -3.4,
    frustration: 2.1,
    urgency: 1.4,
    social: 1.7,
    family: 1.8,
    progress: 0.6,
    complexityPenalty: 0.8
  }
};
