import React from "react";
import { Composition } from "remotion";
import { BridgeShort, BRIDGE_FRAMES } from "./videos/bridge/Bridge";
import { HelgolandShort, HELGO_FRAMES } from "./videos/helgoland/Helgoland";

export const Root: React.FC = () => (
  <>
    <Composition id="BridgeShort" component={BridgeShort} durationInFrames={BRIDGE_FRAMES} fps={30} width={1080} height={1920} />
    <Composition id="Helgoland" component={HelgolandShort} durationInFrames={HELGO_FRAMES} fps={30} width={1080} height={1920} />
  </>
);
