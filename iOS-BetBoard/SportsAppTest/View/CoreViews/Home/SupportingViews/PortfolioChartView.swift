//
//  PortfolioChartView.swift
//  SportsAppTest
//
//  Created by Trenton Roney on 9/22/25.
//


import SwiftUI
import Charts

struct PortfolioChartView: View {
    let chartData: [ChartDataPoint]
    let totalPnL: Double
    let totalPnLFormatted: String
    let roiFormatted: String
    @Binding var selectedTimeframe: TimeFrame
    let onTimeframeChange: (TimeFrame) -> Void
    
    @State private var selectedDate: Date?  // ADD THIS
    
    var body: some View {
        VStack(alignment: .leading, spacing: 16) {
            HStack {
                Text("Portfolio Performance")
                    .font(.headline)
                    .fontWeight(.semibold)
                Spacer()
            }
            
            // Overall P&L Display
            VStack(alignment: .leading, spacing: 8) {
                HStack {
                    Text("Total P&L")
                        .font(.subheadline)
                        .foregroundColor(.secondary)
                    Spacer()
                    Text(totalPnLFormatted)
                        .font(.title2)
                        .fontWeight(.bold)
                        .foregroundColor(totalPnL >= 0 ? .green : .red)
                }
                
                HStack {
                    Text("ROI")
                        .font(.subheadline)
                        .foregroundColor(.secondary)
                    Spacer()
                    Text(roiFormatted)
                        .font(.subheadline)
                        .fontWeight(.medium)
                        .foregroundColor(totalPnL >= 0 ? .green : .red)
                }
            }
            .padding()
            .background(Color(.systemGray6))
            .cornerRadius(12)
            
            // Time Frame Selector
            HStack {
                ForEach(TimeFrame.allCases, id: \.self) { timeframe in
                    Button(action: {
                        selectedTimeframe = timeframe
                        onTimeframeChange(timeframe)
                    }) {
                        Text(timeframe.displayName)
                            .font(.caption)
                            .fontWeight(.medium)
                            .foregroundColor(selectedTimeframe == timeframe ? .white : .primary)
                            .padding(.horizontal, 12)
                            .padding(.vertical, 6)
                            .background(selectedTimeframe == timeframe ? Color.blue : Color(.systemGray5))
                            .cornerRadius(8)
                    }
                }
            }
            
            // ADD: Show selected point info
            if let selectedDateValue = selectedDate,
               let dataPoint = chartData.first(where: { Calendar.current.isDate($0.date, inSameDayAs: selectedDateValue) }) {
                HStack {
                    VStack(alignment: .leading, spacing: 2) {
                        Text(formatDate(dataPoint.date))
                            .font(.caption)
                            .foregroundColor(.secondary)
                        Text(formatCurrency(dataPoint.pnl))
                            .font(.headline)
                            .fontWeight(.bold)
                            .foregroundColor(dataPoint.pnl >= 0 ? .green : .red)
                    }
                    Spacer()
                    Button("Clear") {
                        selectedDate = nil
                    }
                    .font(.caption)
                    .foregroundColor(.blue)
                }
                .padding(.horizontal, 12)
                .padding(.vertical, 8)
                .background(Color(.systemGray6))
                .cornerRadius(8)
            }
            
            // Chart
            Chart(chartData) { dataPoint in
                AreaMark(
                    x: .value("Date", dataPoint.date),
                    yStart: .value("Start", 0),
                    yEnd: .value("P&L", dataPoint.pnl)
                )
                .foregroundStyle(
                    LinearGradient(
                        colors: [
                            (totalPnL >= 0 ? Color.green : Color.red).opacity(0.2),
                            (totalPnL >= 0 ? Color.green : Color.red).opacity(0.0)
                        ],
                        startPoint: .top,
                        endPoint: .bottom
                    )
                )
                .interpolationMethod(.monotone)
                
                LineMark(
                    x: .value("Date", dataPoint.date),
                    y: .value("P&L", dataPoint.pnl)
                )
                .foregroundStyle(totalPnL >= 0 ? .green : .red)
                .lineStyle(StrokeStyle(lineWidth: 3, lineCap: .round, lineJoin: .round))
                .interpolationMethod(.monotone)
                
                // ADD: Show selected point
                if let selectedDateValue = selectedDate,
                   let selected = chartData.first(where: { Calendar.current.isDate($0.date, inSameDayAs: selectedDateValue) }) {
                    RuleMark(x: .value("Selected", selected.date))
                        .foregroundStyle(.gray.opacity(0.5))
                        .lineStyle(StrokeStyle(lineWidth: 1, dash: [5, 5]))
                    
                    PointMark(
                        x: .value("Date", selected.date),
                        y: .value("P&L", selected.pnl)
                    )
                    .foregroundStyle(totalPnL >= 0 ? .green : .red)
                    .symbolSize(100)
                }
            }
            .frame(height: 200)
            .chartXSelection(value: $selectedDate)  // ADD THIS - enables tap/drag selection
            .chartXAxis {
                AxisMarks(values: .automatic) { value in
                    AxisGridLine()
                    AxisValueLabel(format: .dateTime.month(.abbreviated).day())
                }
            }
            .chartYAxis {
                AxisMarks { value in
                    AxisGridLine()
                    AxisValueLabel {
                        if let doubleValue = value.as(Double.self) {
                            Text(formatCurrency(doubleValue))
                        }
                    }
                }
            }
        }
        .padding()
        .background(Color(.systemBackground))
        .cornerRadius(16)
        .shadow(color: .black.opacity(0.1), radius: 4, x: 0, y: 2)
    }
    
    private func formatCurrency(_ value: Double) -> String {
        let formatter = NumberFormatter()
        formatter.numberStyle = .currency
        formatter.currencySymbol = "$"
        formatter.maximumFractionDigits = 0
        return formatter.string(from: NSNumber(value: value)) ?? "$0"
    }
    
    // ADD THIS helper
    private func formatDate(_ date: Date) -> String {
        let formatter = DateFormatter()
        formatter.dateFormat = "MMM d, yyyy"
        return formatter.string(from: date)
    }
}
