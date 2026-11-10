// Opening the toolbar action grants activeTab access for the current page.
// Page text is read only after the user chooses to import it in the panel.
chrome.sidePanel.setPanelBehavior({ openPanelOnActionClick: true }).catch((error) => {
  console.warn("Mochi Reader could not enable the side panel:", error.message);
});
