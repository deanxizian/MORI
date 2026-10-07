import UIKit
import Capacitor

@main
class AppDelegate: UIResponder, UIApplicationDelegate {
    func application(_ application: UIApplication, didFinishLaunchingWithOptions launchOptions: [UIApplication.LaunchOptionsKey: Any]?) -> Bool { true }
}

// Single scene for MORI. Required by the installed iOS 27 SDK. On inactivity
// the web client stops renewal; MCU expiry still handles a suspended JS thread.
class SceneDelegate: UIResponder, UIWindowSceneDelegate {
    var window: UIWindow?
    func sceneWillResignActive(_ scene: UIScene) {
        (window?.rootViewController as? CAPBridgeViewController)?.bridge?.triggerJSEvent(eventName: "moriNativeInactive", target: "window")
    }
    func sceneDidEnterBackground(_ scene: UIScene) {
        (window?.rootViewController as? CAPBridgeViewController)?.bridge?.triggerJSEvent(eventName: "moriNativeInactive", target: "window")
    }
    func scene(_ scene: UIScene, openURLContexts contexts: Set<UIOpenURLContext>) {
        for context in contexts {
            _ = ApplicationDelegateProxy.shared.application(UIApplication.shared, open: context.url, options: [:])
        }
    }
    func scene(_ scene: UIScene, continue userActivity: NSUserActivity) {
        _ = ApplicationDelegateProxy.shared.application(UIApplication.shared, continue: userActivity, restorationHandler: { _ in })
    }
}
