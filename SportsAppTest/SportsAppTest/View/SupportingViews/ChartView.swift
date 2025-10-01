//
//  ChartView.swift
//  SportsAppOG
//
//  Created by Trenton Roney on 8/26/25.
//

//
//  ChartView.swift
//  SportsApp
//
//  Created by Trenton Roney on 7/2/25.
//
import SwiftUI
import Charts

// Sample Data Model
struct BetDataPoint: Identifiable {
    let id = UUID()
    let date: Date
    let value: Double // Total profit/loss at that point in time
}

// Time ranges
enum TimeFilter: String, CaseIterable {
    case oneDay = "1D", oneWeek = "1W", oneMonth = "1M", threeMonths = "3M", oneYear = "1Y", fiveYears = "5Y", all = "All"
    
    var days: Int {
        switch self {
        case .oneDay: return 1
        case .oneWeek: return 7
        case .oneMonth: return 30
        case .threeMonths: return 90
        case .oneYear: return 365
        case .fiveYears: return 365 * 5
        case .all: return .max
        }
    }
}

struct SportsbookChartView: View {
    let allData: [BetDataPoint]
    let title: String
    
    @State private var selectedFilter: TimeFilter = .oneMonth

    private var filteredData: [BetDataPoint] {
        guard selectedFilter != .all else { return allData }
        let cutoff = Calendar.current.date(byAdding: .day, value: -selectedFilter.days, to: Date())!
        return allData.filter { $0.date >= cutoff }
    }
    
    private var totalPL: Double {
        filteredData.last?.value ?? 0
    }
    
    var body: some View {
        VStack(alignment: .leading, spacing: 16) {
            Text(title)
                .font(.headline)
                .padding(.horizontal)
            
            Text("Total P/L: \(totalPL >= 0 ? "+" : "")$\(String(format: "%.2f", totalPL))")
                .font(.title2)
                .bold()
                .foregroundColor(totalPL >= 0 ? .green : .red)
                .padding(.horizontal)

            Chart(filteredData) {
                LineMark(
                    x: .value("Date", $0.date),
                    y: .value("P/L", $0.value)
                )
                .interpolationMethod(.monotone)
                .foregroundStyle(totalPL >= 0 ? Color.green : Color.red)
            }
            .chartYAxis {
                AxisMarks(position: .leading)
            }
            .frame(height: 200)
            .padding(.horizontal)

            // Filter Buttons
            HStack(spacing: 12) {
                ForEach(TimeFilter.allCases, id: \.self) { filter in
                    Button(action: {
                        selectedFilter = filter
                    }) {
                        Text(filter.rawValue)
                            .font(.caption)
                            .padding(.vertical, 4)
                            .padding(.horizontal, 8)
                            .background(selectedFilter == filter ? Color.blue.opacity(0.2) : Color.clear)
                            .cornerRadius(6)
                    }
                }
            }
            .padding(.horizontal)
        }
        .padding(.vertical)
    }
}
