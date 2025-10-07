//
//  Enums.swift
//  SportsAppOG
//
//  Created by Trenton Roney on 8/26/25.
//

//
//  Enums.swift
//  SportsApp
//
//  Created by Trenton Roney on 7/14/25.
//

import Foundation

enum BetType: String, Codable {
    case moneyline
    case spread
    case total
}

enum BetResult: String, Codable {
    case won
    case lost
    case push
    case pending
}

enum GameStatus: Codable {
    case notPlayed
    case inProgress
    case final(home: Int, away: Int)

    enum CodingKeys: String, CodingKey {
        case state, homeScore, awayScore
    }

    enum StateValue: String, Codable {
        case NP
        case IP
        case FINAL
    }

    init(from decoder: Decoder) throws {
        let container = try decoder.container(keyedBy: CodingKeys.self)
        let state = try container.decode(StateValue.self, forKey: .state)

        switch state {
        case .NP:
            self = .notPlayed
        case .IP:
            self = .inProgress
        case .FINAL:
            let home = try container.decode(Int.self, forKey: .homeScore)
            let away = try container.decode(Int.self, forKey: .awayScore)
            self = .final(home: home, away: away)
        }
    }

    func encode(to encoder: Encoder) throws {
        var container = encoder.container(keyedBy: CodingKeys.self)

        switch self {
        case .notPlayed:
            try container.encode(StateValue.NP, forKey: .state)
        case .inProgress:
            try container.encode(StateValue.IP, forKey: .state)
        case .final(let home, let away):
            try container.encode(StateValue.FINAL, forKey: .state)
            try container.encode(home, forKey: .homeScore)
            try container.encode(away, forKey: .awayScore)
        }
    }
}
