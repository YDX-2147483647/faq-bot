
#set page(
  width: 900pt,
  height: 1600pt,
  // 供图：技术部硅硅草，2025年11月18日凌晨
  background: image("background.png", width: 100%),
)

#set text(
  lang: "zh",
  region: "CN",
  font: "HYRuiYunXiuWu", // 汉仪瑞云袖舞
  bottom-edge: "descender",
  top-edge: "ascender",
)


#rotate(-10deg, {
  set text(size: 100pt, fill: rgb("ff9ea8"))
  show: move.with(dx: -1em)
  show: block.with(width: 5em)
  set align(center)

  let body = sys.inputs.at("body", default: "哈！")
  place(top + center, {
    set text(
      stroke: (paint: white, thickness: 1em / 3, miter-limit: 1, join: "round"),
      fill: white,
    )
    body
  })
  body
})
