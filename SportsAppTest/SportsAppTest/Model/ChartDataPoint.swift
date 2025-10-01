//
//  ChartDataPoint.swift
//  SportsAppTest
//
//  Created by Trenton Roney on 9/22/25.
//

import Foundation
import SwiftUI

// MARK: - Chart Data Point
struct ChartDataPoint: Identifiable {
    let id = UUID()
    let date: Date
    let pnl: Double
}
