//
//  SettingsToggleView.swift
//  SportsAppTest
//
//  Created by Trenton Roney on 9/22/25.
//


//
//  SettingsToggleView.swift
//  SportsAppOG
//
//  Created by Trenton Roney on 8/26/25.
//

import SwiftUI

struct SettingsToggleView: View {
    let icon: String
    let iconColor: Color
    let title: String
    @Binding var isOn: Bool
    
    var body: some View {
        SettingsRowView(
            icon: icon,
            iconColor: iconColor,
            title: title
        ) {
            Toggle("", isOn: $isOn)
        }
    }
}

#Preview {
    List {
        SettingsToggleView(
            icon: "bell",
            iconColor: .orange,
            title: "Notifications",
            isOn: .constant(true)
        )
        
        SettingsToggleView(
            icon: "moon",
            iconColor: .purple,
            title: "Dark Mode",
            isOn: .constant(false)
        )
    }
}