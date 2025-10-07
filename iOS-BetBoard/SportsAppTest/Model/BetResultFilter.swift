//
//  BetResultFilter.swift
//  SportsAppTest
//
//  Created by Trenton Roney on 9/22/25.
//

import Foundation
import SwiftUI

enum BetResultFilter: String, CaseIterable {
    case all = "All"
    case won = "Won"
    case lost = "Lost"
    case pending = "Pending"
    case push = "Push"
    
    var displayName: String {
        return self.rawValue
    }
}

enum SortOption: String, CaseIterable {
    case dateNewest = "Date (Newest)"
    case dateOldest = "Date (Oldest)"
    case amountHighest = "Amount (Highest)"
    case amountLowest = "Amount (Lowest)"
    
    var displayName: String {
        return self.rawValue
    }
}
