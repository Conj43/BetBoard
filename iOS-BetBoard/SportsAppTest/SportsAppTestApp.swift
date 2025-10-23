

//
//  SportsAppTestApp.swift
//  SportsAppTest
//
//  Created by Trenton Roney on 8/1/25.
//


import SwiftUI
import Firebase
import GoogleSignIn

@main
struct SportsAppTestApp: App {
    
    init() {
        FirebaseApp.configure()
        if let clientID = FirebaseApp.app()?.options.clientID {
                    GIDSignIn.sharedInstance.configuration = GIDConfiguration(clientID: clientID)
                }
    }
    
    var body: some Scene {
        WindowGroup {
            ContentView()
        }
    }
}
