# GPS Attack Simulation Design Practices

## DESIGN-01 Multiple Classes
Divide code into several classes that each have a useful purpose (i.e., beyond just get/set methods). Avoid these code smells: large class and data clumps.

## DESIGN-02 Meaningful Names
Give variables, methods, classes, and packages non-abbreviated, intention-revealing names to support Clean Code and reduce the need for comments.

## DESIGN-03 Named Constants
Name constant values, including numbers and strings, used multiple times or in program logic. This includes being declared as final variables with an intention revealing name.

## DESIGN-04 Don’t Repeat Yourself (DRY)
The same lines of code should not appear in multiple different places in the same project (i.e., they should not be duplicated). Instead, the code should be refactored so that the duplicated logic is written only once and called from many places.

## DESIGN-05 Interact Through Methods
Classes should avoid inappropriate intimacy by collaborating via method calls. A class should not directly access the instance variables of another class. Do not use public instance variables or global variables.

## DESIGN-06 Code Formatting
Code should follow course formatting conventions, including things that cannot be automatically checked, especially the Java naming conventions.

## DESIGN-07 Tightly Scoped Methods
Each method should be small with a single-purpose. Long methods should be decomposed into smaller pieces of functionality. Long methods are a code smell.

## DESIGN-08 Comments
Follow Javadoc conventions for commenting on public classes, interfaces, methods, and packages. In-line comments should be used judiciously; self-explanatory code is preferred. See Internal Documentation.

## DESIGN-09 Model View Separation
GUIs should be separate from the model; this requires clear articulation about what information (including errors) needs to be communicated between each part.

## DESIGN-10 Encapsulation
Key implementation details must be hidden such that they can be changed without impacting any other classes.

## DESIGN-11 Make and Use Abstractions
Create abstractions that capture commonality (superclasses or interfaces) and encourage variability (subclasses or implementors). Build your classes to depend on the abstractions (superclasses and interfaces) rather than implementations (concrete subclasses).

## DESIGN-12 Automated Testing
Your program must be tested using JUnit (with assertions both for typical situations and possible thrown Exceptions) to verify it works as intended. Tests should be written in separate classes and methods that follow these naming standards. These tests should be a mix of:

    1. Model Tests: tests that test one small unit of functionality
    2. End-to-End Tests: tests that simulate the user interacting with user interface (e.g., using TestFX)

## DESIGN-13 Programs Should Not Crash
Build robustness into your program so that it does not crash or hang. Handle errors and provide a reasonable response to exceptional cases so that the user can continue to run the program.

## DESIGN-14 Handle Errors Using Exception Flows
Communicate errors in a thoughtful, intentional, manner rather than returning null or other error prone values. Consider using custom Exceptions or Java's Optional.

## DESIGN-15 Externalize Configuration
Move hardcoded values into configuration files, rather than compiled into your program, specifically:
    1. "magic" values stored as static final constants
    2. any text displayed in the user interface, by using resource property files (the String.format() method allows you to make any complex string a single value)
    3. any styles (colors, font, borders, etc.) used to customize the user interface, by using CSS files

## DESIGN-16 No Dead Code
Your project should not include unused variables, methods, or classes. Do not comment out blocks of code to save them for later; instead, use your GIT history to find old code.

## DESIGN-17 Explicit Immutability
For classes and values that should not change after they are instantiated, explicitly restrict them from changing using language features. Consider using Enumerated types or Records.

## DESIGN-18 APIs
Provide well-defined Application Programming Interfaces (APIs) for logical parts of your project. Each public API class and method should have complete Javadoc comments, especially interfaces and abstract classes to show their intended use. Each API package must include a file called package-info.java that includes comments to describe the API's Design Goals and Contracts.

## DESIGN-19 Apply Design Patterns
Define and describe your system design using Design Patterns.
Your classes should follow the naming conventions of the design pattern you are applying (i.e., a factory class from the Factory pattern should be named with the suffix Factory).
Document your Design Patterns where appropriate, such as Javadoc comments and the project DESIGN document.

## DESIGN-20 Reflection for Instantiation from Strings
Use reflection whenever you need to create objects or call methods from Strings rather than hardcoding conditionals or a mapping between the String literal and your object.

## DESIGN-21 Logging
Use Log4j2, instead of println() statements to output messages. A message must be generated any time an Exception is thrown that is saved to one or more files within the folder log. Messages labeled as DEBUG or INFO can go to the console (standard out) or a file.