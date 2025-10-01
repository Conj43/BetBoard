//
//  SettingsRowView.swift
//  SportsAppTest
//
//  Created by Trenton Roney on 9/22/25.
//


//
//  SettingsRowView.swift
//  SportsAppOG
//
//  Created by Trenton Roney on 8/26/25.
//

import SwiftUI

struct SettingsRowView<Content: View>: View {
    let icon: String
    let iconColor: Color
    let title: String
    let titleColor: Color
    let content: () -> Content
    
    init(
        icon: String,
        iconColor: Color,
        title: String,
        titleColor: Color = .primary,
        @ViewBuilder content: @escaping () -> Content = { EmptyView() }
    ) {
        self.icon = icon
        self.iconColor = iconColor
        self.title = title
        self.titleColor = titleColor
        self.content = content
    }
    
    var body: some View {
        HStack {
            Image(systemName: icon)
                .foregroundColor(iconColor)
                .frame(width: 25)
            
            Text(title)
                .foregroundColor(titleColor)
            
            Spacer()
            
            content()
        }
    }
}

#Preview {
    List {
        SettingsRowView(
            icon: "bell",
            iconColor: .orange,
            title: "Notifications"
        ) {
            Toggle("", isOn: .constant(true))
        }
        
        SettingsRowView(
            icon: "info.circle",
            iconColor: .blue,
            title: "About App"
        )
        
        SettingsRowView(
            icon: "rectangle.portrait.and.arrow.right",
            iconColor: .red,
            title: "Sign Out",
            titleColor: .red
        )
    }
}