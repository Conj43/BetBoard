//
//  TimeFrame.swift
//  SportsAppTest
//
//  Created by Trenton Roney on 9/22/25.
//

import Foundation
import SwiftUI

// MARK: - Time Frame Enum
enum TimeFrame: String, CaseIterable {
    case oneDay = "1D"
    case oneWeek = "1W"
    case oneMonth = "1M"
    case threeMonths = "3M"
    case ytd = "YTD"
    case allTime = "All"
    
    var displayName: String {
        return self.rawValue
    }
}
