// See also welcome.typ.
// https://gist.github.com/ParaN3xus/b0b6988a823e13b24a8398acccf034cc

#let headline = sys.inputs.at("headline", default: "")

#set page(width: auto, height: auto, margin: 1em)
#set text(
  font: "Noto Serif CJK SC",
  lang: "zh",
  top-edge: "ascender",
  bottom-edge: "descender",
)

#import "@preview/cetz:0.4.0"
#set page(background: place(top + center, {
  let h = 90pt
  let r = 300pt
  let n = 42

  v(-r + h)
  cetz.canvas({
    import cetz.draw: *

    set-style(arc: (radius: r, mode: "PIE", stroke: none))

    for i in range(n) {
      let θ = 360deg * i / n
      arc(
        (r * calc.cos(θ), r * calc.sin(θ)),
        start: θ - 3deg,
        delta: 360deg / n,
        fill: if calc.even(i) { purple.lighten(50%) } else {
          green.lighten(50%)
        },
      )
    }
  })
}))

#set align(center)

#{
  // The height should be fixed for page.background.
  let message = [#box(height: 1em, headline)\ 出门左转 \ *Typst 中文聊天室*]

  place(top + center, {
    set text(stroke: (paint: white, thickness: 1em / 3, miter-limit: 1), fill: white)
    message
  })
  message

  v(-0.5em)

  import "@preview/tiaoma:0.3.0": qrcode
  box(fill: white, inset: 1em / 4, qrcode("https://qm.qq.com/q/gYgU5vgbRK"))
}

#let off-topic(rem: 12pt) = box(
  stroke: black + rem / 4,
  radius: rem,
  inset: rem / 20,
  box(
    fill: yellow.lighten(50%),
    stroke: red + rem / 4,
    inset: (x: rem / 2, y: rem),
    radius: rem,
    {
      set text(
        font: "Libertinus Serif",
        weight: "black",
        fill: red,
        size: rem * 3,
        stroke: luma(25%) + rem / 20,
        fallback: false,
      )
      box(stroke: (y: red + rem / 4), inset: (x: rem / 4), smallcaps[Off Topic])
    },
  ),
)


#grid(
  ..range(6).map(row => {
    let n = calc.pow(2, row)
    let shrink = if n == 1 { 100% } else { 95% }
    block(inset: (y: 4pt / n), range(n)
      .map(i => off-topic(rem: 12pt / n * shrink))
      .intersperse(h(1fr))
      .join())
  })
)
#v(-1em)
