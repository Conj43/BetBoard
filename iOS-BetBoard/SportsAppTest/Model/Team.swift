//
//  Team.swift
//  SportsAppOG
//
//  Created by Trenton Roney on 8/26/25.
//

import Foundation

struct Team: Identifiable, Codable {
    let id: String
    let name: String
    let shortName: String
    let logoURL: String
    let record: TeamRecord
    let conference: String
    let ranking: Int?
    let colorHex: String?
}

struct TeamRecord: Codable {
    let wins: Int
    let losses: Int
}
