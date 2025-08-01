//
//  BetTypeExtensions.swift
//  SportsAppOG
//
//  Created by Trenton Roney on 8/26/25.
//

import Foundation

// MARK: - BetType Extension
extension BetType {
    var displayName: String {
        switch self {
        case .moneyline:
            return "Moneyline"
        case .spread:
            return "Spread"
        case .total:
            return "Total"
        }
    }
}
