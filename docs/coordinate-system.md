# Coordinate System Guide

This project intentionally keeps domain coordinates separate from display coordinates. Most coordinate bugs come from saving a value in one coordinate system and later reading it as another one, so every persisted point should name its coordinate system in the field name or API contract.

## 1. Image pixel coordinate

**Source:** frame images, detection bounding boxes, and calibration image points.

**Range:** `x = 0..image width`, `y = 0..image height` for the specific frame image. The origin is the top-left image pixel. `x` increases to the right and `y` increases downward.

**Used by:** backend homography estimation/projection and image-space overlays.

**Examples in the app:**

- Calibration `image_point` values are saved as real frame pixel coordinates.
- Detection `box` values and track `image_point_x` / `image_point_y` values are image pixel coordinates.
- Backend homography consumes image pixel coordinates and maps them to court feet.

### Calibration click conversion

The user clicks a rendered image that may be scaled by CSS. Convert from browser display pixels back into the natural frame image before saving:

```ts
const rect = imageElement.getBoundingClientRect()
const displayX = event.clientX - rect.left
const displayY = event.clientY - rect.top

const imageX = (displayX / rect.width) * imageElement.naturalWidth
const imageY = (displayY / rect.height) * imageElement.naturalHeight

const imagePoint = { x: imageX, y: imageY }
```

Persist `imagePoint` as image pixel coordinate data, not as CSS pixels.

## 2. Normalized image coordinate

**Source:** future quiz arrows and portable UI annotations.

**Range:** `x = 0..1`, `y = 0..1`, relative to the frame image dimensions. The origin remains the top-left of the image. `x` increases to the right and `y` increases downward.

**Used by:** UI annotation portability across resized images, thumbnails, and different display densities.

Normalized points should be used when an annotation belongs to an image but should survive display resizing. They should not be passed directly into homography code without first converting back to image pixels.

### Arrow normalized conversion

When the user draws a quiz arrow on a scaled image, save normalized points:

```ts
const startNormalized = {
  x: startImagePixel.x / imageWidth,
  y: startImagePixel.y / imageHeight
}

const endNormalized = {
  x: endImagePixel.x / imageWidth,
  y: endImagePixel.y / imageHeight
}
```

When rendering that arrow later on any image size, convert normalized data into the current displayed image space:

```ts
const startDisplay = {
  x: startNormalized.x * renderedImageWidth,
  y: startNormalized.y * renderedImageHeight
}

const endDisplay = {
  x: endNormalized.x * renderedImageWidth,
  y: endNormalized.y * renderedImageHeight
}
```

## 3. Court feet coordinate

**Source:** homography projection from image pixels to basketball court geometry.

**Range:** `x = 0..94`, `y = 0..50` for a full NBA-style court in feet. The app's 2D court view uses a full-court model where length is 94 feet and width is 50 feet.

**Used by:** `Court2DView` and any domain logic that compares player locations on the court.

Court feet coordinates are domain data. They can be persisted as `court_x` / `court_y` because they do not depend on the screen, browser zoom, or SVG size.

### Projected court rendering

Projected tracking points arrive as court feet:

```json
{
  "court_x": 47.2,
  "court_y": 24.8
}
```

Render them in an SVG with a matching court-feet viewBox:

```vue
<svg viewBox="0 0 94 50">
  <circle :cx="point.court_x" :cy="point.court_y" r="0.6" />
</svg>
```

If a different SVG viewBox is used, convert court feet into that display coordinate system at render time only.

## 4. SVG display coordinate

**Source:** the rendering layer.

**Range:** depends on the SVG `viewBox`, CSS size, pan/zoom transform, and component-specific scaling.

**Used by:** drawing court lines, circles, labels, paths, and temporary UI handles.

SVG display coordinates should not be persisted as domain data. They are a presentation detail. Persist image pixels for image-space domain data, normalized image coordinates for portable image annotations, and court feet for projected court-domain data.

## Quick conversion checklist

- Browser click on frame ➜ convert display pixels to **image pixel coordinate** before calibration save.
- Quiz arrow on frame ➜ convert image/display position to **normalized image coordinate** before saving the prompt.
- Tracking point for court view ➜ backend projects **image pixel coordinate** through homography into **court feet coordinate**.
- Court rendering ➜ convert **court feet coordinate** to **SVG display coordinate** only inside the view component.
