//
//  User.swift
//  SportsAppOG
//
//  Created by Trenton Roney on 8/26/25.
//


//
//  User.swift
//  SportsApp
//
//  Created by Trenton Roney on 7/14/25.
//


import Foundation

struct User: Identifiable, Codable {
    let id: String
    let username: String
    let email: String?
    let trackedBetIDs: [String]
    let createdAt: Date
}

// Firebase Implementation
// {
//   "id": "user456",
//   "username": "Trenton",
//   "email": "trenton@example.com",
//   "trackedBetIDs": ["bet123", "bet124"],
//   "createdAt": "2024-01-15T12:00:00Z"
// }
