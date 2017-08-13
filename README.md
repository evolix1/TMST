# TMST
Text Marker Scrapper Template

> ** EARLY ALPHA ** version

## What is it ?

It simplifies information capture within a DOM structure.

## What does it look like ?

### Simple templates

This first example extracts all image's url.

```xml
<img src:{picture} />
```

Ok fine, but this is no better than XPath.

<br/>

This second example groups extraction within a identified scope.

One main thing to know, __parent/child relationship in the template is not direct__.
Between `card` and `card-title` in the source DOM to parse, there can be 0 to &infin; intermediate level.
Same thing append with `img`, it can be or not sibling with `span`.

```xml
<#:{item} class="card" />
    <span class="card-title">{item.title}/</span>
    <img src:{item.picture} />
</>
```

### Advance template

```xml
<#:{item} class="content-item">
    <a:{item.preview} class="preview" href:{item.link}>
        <img src:{item.preview.pic} />
        <# class="title">
            <span>{item.preview.title}</span>
        </>
    </a>
    <a class="link" href:{item.link}>
        {item.description}
    </a>
<#/>
```

is equivalent as

```xml
<#:{item} class="content-item">
    <a:{.preview} class="preview" href:{.link}>
        <img src:{.pic} />
        <# class="title">
            <span>{.title}</span>
        </>
    </a>
    <a class="link" href:{.link}>
        {.description}
    </a>
</>
```

* Autoclosing tag of `#`.
* Relative capture name. `item.pic` become `.pic`.

## Syntax

#### Capture

Attribute are captured like this `attribute:{name_for_capture}` _(no space/quote possible at any position here)_.

Text are captured with `{name_for_capture}`. This expression is between an opening and closing tag.

<br/>

A capture name is understood as a namespace path.

Capture names `item.description` ,`item.preview.link`, `item.preview.title` are decomposed as:

+ `item` is a top-level object,
    + `preview` is a list of top-level object,
        + `link` is a list of url (as text),
        + `title` is a list of text,
    + `description` is a list of text,


#### Tag matching

Tag name are matched as given. A written tag `span` must match an existing source DOM element named `span`.

In case any tag is possible, use `#`.

#### Attribute matching

Attribute are matched with the equal operator `==`.

Exception of the `class` attribute. All classes given are parsed. Any source DOM element's `class` attribute must contains all the given classes.

## License

See the `LICENSE` file.