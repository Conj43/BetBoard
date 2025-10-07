//
//  Team.swift
//  SportsAppOG
//
//  Created by Trenton Roney on 8/26/25.
//


//
//  Team.swift
//  SportsApp
//
//  Created by Trenton Roney on 7/14/25.
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
// Firebase Implementation
// {
//   "id": "DUKE",
//   "name": "Duke Blue Devils",
//   "shortName": "DUKE",
//   "logoURL": "https://yourbucket.s3.amazonaws.com/logos/duke.png",
//   "record": {
//     "wins": 23,
//     "losses": 8
//   },
//   "conference": "ACC",
//   "ranking": 9,
//   "colorHex": "#001A57"
// }