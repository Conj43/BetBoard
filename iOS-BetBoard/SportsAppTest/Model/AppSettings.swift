//
//  AppSettings.swift
//  SportsAppOG
//
//  Created by Trenton Roney on 8/26/25.
//


//
//  AppSettings.swift
//  SportsApp
//
//  Created by Trenton Roney on 7/14/25.
//


import Foundation

struct AppSettings: Codable {
    let userID: String
    var notificationsEnabled: Bool
    var darkModeEnabled: Bool
    var preferredOddsFormat: OddsFormat
}

enum OddsFormat: String, Codable {
    case american
    case decimal
    case fractional
}

// Firebase Implementation
// {
//   "userID": "user456",
//   "notificationsEnabled": true,
//   "darkModeEnabled": false,
//   "preferredOddsFormat": "american"
// }