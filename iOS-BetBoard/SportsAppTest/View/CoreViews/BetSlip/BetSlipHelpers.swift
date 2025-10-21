//
//  BetSlipHelpers.swift
//  SportsAppTest
//
//  Created by Trenton Roney on 10/1/25.
//


import Foundation

struct BetSlipHelpers {
    static func formatOdds(_ odds: Double) -> String {
        if odds > 0 {
            return "+\(Int(odds))"
        } else {
            return "\(Int(odds))"
        }
    }
    
    static func calculatePayout(amount: Double, odds: Double) -> Double {
        if odds > 0 {
            return amount * (odds / 100) + amount
        } else {
            return amount * (100 / abs(odds)) + amount
        }
    }
}
