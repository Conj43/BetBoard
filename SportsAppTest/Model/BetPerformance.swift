//
//  BetPerformance.swift
//  SportsAppOG
//
//  Created by Trenton Roney on 8/26/25.
//


//
//  BetPerformance.swift
//  SportsApp
//
//  Created by Trenton Roney on 7/14/25.
//


import Foundation

struct BetPerformance: Codable {
    let userID: String
    let totalBets: Int
    let wins: Int
    let losses: Int
    let pushes: Int
    let roi: Double
    let lastUpdated: Date
}

// Firebase Implementation
// {
//   "userID": "user456",
//   "totalBets": 50,
//   "wins": 30,
//   "losses": 18,
//   "pushes": 2,
//   "roi": 12.5,
//   "lastUpdated": "2025-07-01T10:00:00Z"
// }