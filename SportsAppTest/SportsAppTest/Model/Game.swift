//
//  Game.swift
//  SportsAppOG
//
//  Created by Trenton Roney on 8/26/25.
//


//
//  Game.swift
//  SportsApp
//
//  Created by Trenton Roney on 7/14/25.
//

import Foundation

struct Game: Identifiable, Codable {
    let id: String
    let homeTeam: String
    let awayTeam: String
    let date: Date
    let status: GameStatus
    let neutralSite: Bool

    var formattedDate: String {
        let formatter = DateFormatter()
        formatter.dateFormat = "MM/dd/yyyy - h:mm a"
        return formatter.string(from: date)
    }

    var scoreText: String {
        switch status {
        case .notPlayed: return "NP"
        case .inProgress: return "IP"
        case .final(let home, let away): return "\(home) - \(away)"
        }
    }
}

// Firebase Implementation
// {
//   "id": "game123",
//   "homeTeam": "Duke",
//   "awayTeam": "UNC",
//   "date": "2025-07-14T18:30:00Z",
//   "neutralSite": true,
//   "status": {
//     "state": "FINAL",
//     "homeScore": 72,
//     "awayScore": 68
//   }
// }
