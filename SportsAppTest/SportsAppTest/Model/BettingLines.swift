//
//  BettingLines.swift
//  SportsAppOG
//
//  Created by Trenton Roney on 8/26/25.
//


//
//  BettingLines.swift
//  SportsApp
//
//  Created by Trenton Roney on 7/14/25.
//


import Foundation

struct BettingLines: Identifiable, Codable {
    let id: String
    let gameID: String
    let moneyline: [String: Double] // e.g. {"Duke": -130, "UNC": 110}
    let spread: [String: Double]    // e.g. {"Duke -3.5": -110, "UNC +3.5": -110}
    let total: [String: Double]     // e.g. {"Over 145.5": -110, "Under 145.5": -110}
}


// Firebase Implementation
// {
//   "id": "game123",
//   "gameID": "game123",
//   "moneyline": {
//     "Duke": -130,
//     "UNC": 110
//   },
//   "spread": {
//     "Duke -3.5": -110,
//     "UNC +3.5": -110
//   },
//   "total": {
//     "Over 145.5": -110,
//     "Under 145.5": -110
//   }
// }